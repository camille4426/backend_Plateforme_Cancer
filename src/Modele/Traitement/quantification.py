import os
import base64
import numpy as np

from src.logger import get_logger
from src.Modele.mrsi import MRSI

from fsl_mrs.core.mrsi import MRSI as FSL_MRSI
import fsl_mrs.utils.mrs_io as mrs_io
from fsl_mrs.utils.misc import calculateAxes
from fsl_mrs.utils import fitting, misc

from scipy.optimize import minimize

from src.Modele.Quantification_Core.mcmc import (
    MCMC_ber_laplace_MH_within_Gibbs,
    objective_function,
    grad
)

from src.Modele.Quantification_Core.tools_mcmc import (
    polynomial_baseline_correction,
    align_mrsi_spectra
)

logger = get_logger(__name__)


class QUANTIFICATION:

    def __init__(self, instance):
        if not isinstance(instance, MRSI):
            raise ValueError("Quantification only works on MRSI data.")
        self.instance = instance
        self.params = {}

    @staticmethod
    def get_catalog_entry():
        return {
            "label": "Quantification",
            "type": ["MRSI"],
            "params": {
                "run_fsl_newton": {"label": "Run FSL Newton", "type": "boolean", "default": True},
                "run_fsl_MH": {"label": "Run FSL MH", "type": "boolean", "default": False},
                "run_mcmc": {"label": "Run Custom MCMC", "type": "boolean", "default": False},
                "roi": {"label": "ROI", "type": "object", "default": None}
            }
        }

    def run(self, run_fsl_newton=True, run_fsl_MH=False, run_mcmc=False, roi=None):

        self.params = {
            "run_fsl_newton": run_fsl_newton,
            "run_fsl_MH": run_fsl_MH,
            "run_mcmc": run_mcmc,
            "roi": roi
        }

        if self.instance.data is None:
            self.instance.load()

        data = self.instance.data
        img = self.instance.img

        if not np.iscomplexobj(data):
            raise ValueError("Quantification requires complex MRSI data.")

        zooms = img.header.get_zooms()
        dwell = zooms[3] if len(zooms) > 3 else 0.001
        bw = 1.0 / dwell
        cf = 123.0e6

        mrsi_fsl = FSL_MRSI(FID=data, cf=cf, bw=bw)

        basis = self._load_basis()
        basis_array_FID = basis.original_basis_array

        if basis_array_FID.shape[0] != data.shape[-1]:
            raise ValueError(
                f"Basis points ({basis_array_FID.shape[0]}) "
                f"do not match data points ({data.shape[-1]})"
            )

        basis_array_spec = np.fft.fftshift(
            np.fft.fft(basis_array_FID, axis=0),
            axes=0
        )

        names = basis._names
        npoints = data.shape[-1]
        t = np.arange(npoints) * dwell

        ppmaxis = self._gen_ppm_axis(npoints, bw, cf)

        aligned = align_mrsi_spectra(
            mrsi_fsl,
            names,
            basis_array_spec,
            ppmaxis
        )

        mrsi_fc = aligned.mrs(basis=basis)

        results = {}

        if run_fsl_newton:
            conc_list, metab_maps = self._run_fsl_newton(mrsi_fc, names, roi)
            results["concentrations"] = conc_list
            results["voxel_maps"] = self._convert_maps(metab_maps)

        if run_fsl_MH:
            results["fsl_MH"] = self._run_fsl_mh(mrsi_fc, names, roi)

        if run_mcmc:
            results["mcmc"] = self._run_mcmc(
                mrsi_fc,
                names,
                ppmaxis,
                basis_array_FID,
                t,
                roi
            )

        return {
            "type": "MRSI",
            **results
        }

    # --------------------------------------------------

    def _load_basis(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        basis_path = os.path.abspath(
            os.path.join(current_dir, "..", "Quantification_Core", "Metabolite_basis_PRESS")
        )

        if not os.path.exists(basis_path):
            raise FileNotFoundError(f"Basis folder not found at: {basis_path}")

        basis = mrs_io.read_basis(basis_path)

        basis.add_peak(
            ppm=1.3,
            amp=10,
            name="Lip",
            gamma=2,
            sigma=2,
            conj=False
        )

        return basis

    def _gen_ppm_axis(self, npoints, bw, cf):
        axes = calculateAxes(bw, cf, npoints, 0)
        return axes["ppm"] + 4.65

    def _convert_maps(self, metab_maps):
        voxel_maps = {}
        affine = self.instance.img.affine

        for metab, vol in metab_maps.items():
            vmin, vmax = np.nanmin(vol), np.nanmax(vol)

            if vmin == vmax:
                norm = np.zeros_like(vol, dtype=np.uint8)
            else:
                norm = ((vol - vmin) / (vmax - vmin) * 255).astype(np.uint8)

            voxel_maps[metab] = {
                "type": "VOXEL_MAP",
                "metabolite": metab,
                "shape": list(vol.shape),
                "data_b64": base64.b64encode(norm.tobytes()).decode("utf-8"),
                "affine": [[float(v) for v in row] for row in affine]
            }

        return voxel_maps

    # --------------------------------------------------

    def _get_ranges(self, spatial_shape, roi):
        x_size, y_size, z_size = spatial_shape

        if roi is None:
            return range(x_size), range(y_size), range(z_size)

        x_r, y_r, z_r = roi
        return (
            [i for i in x_r if 0 <= i < x_size],
            [j for j in y_r if 0 <= j < y_size],
            [k for k in z_r if 0 <= k < z_size]
        )

    # --------------------------------------------------

    def _run_fsl_newton(self, mrsi_fc, names, roi):

        x_range, y_range, z_range = self._get_ranges(mrsi_fc.spatial_shape, roi)
        x_size, y_size, z_size = mrsi_fc.spatial_shape

        metabolite_maps = {
            name: np.zeros((x_size, y_size, z_size), dtype=np.float32)
            for name in names
        }

        results_list = []

        for i in x_range:
            for j in y_range:
                for k in z_range:

                    mrs = mrsi_fc.mrs_by_index([i, j, k])
                    mrs.rescaleForFitting()

                    if np.mean(mrs.FID) == 0:
                        continue

                    mrs.processForFitting()
                    metab_groups = misc.parse_metab_groups(mrs, "combine_all")

                    Fitargs = {
                        "ppmlim": [2, 4],
                        "method": "Newton",
                        "baseline_order": 0,
                        "metab_groups": metab_groups,
                        "model": "voigt"
                    }

                    res = fitting.fit_FSLModel(mrs, **Fitargs)
                    df = res.fitResults.copy()

                    voxel_dict = {"Voxel": (i, j, k)}

                    for metab in names:
                        if metab in df.index:
                            if "Conc" in df.columns:
                                value = float(df.loc[metab, "Conc"])
                            else:
                                value = float(df.loc[metab].values[0])

                            voxel_dict[metab] = value
                            metabolite_maps[metab][i, j, k] = value

                    results_list.append(voxel_dict)

        return results_list, metabolite_maps

    # --------------------------------------------------

    def _run_fsl_mh(self, mrsi_fc, names, roi):

        x_range, y_range, z_range = self._get_ranges(mrsi_fc.spatial_shape, roi)
        results = []

        for i in x_range:
            for j in y_range:
                for k in z_range:

                    mrs = mrsi_fc.mrs_by_index([i, j, k])
                    mrs.rescaleForFitting()

                    if np.mean(mrs.FID) == 0:
                        continue

                    mrs.processForFitting()
                    metab_groups = misc.parse_metab_groups(mrs, "combine_all")

                    Fitargs = {
                        "ppmlim": [2, 4],
                        "method": "MH",
                        "baseline_order": 6,
                        "metab_groups": metab_groups,
                        "model": "voigt",
                        "MHSamples": 5,
                        "maxiter": 50
                    }

                    res = fitting.fit_FSLModel(mrs, **Fitargs)
                    df = res.fitResults.copy()
                    df.insert(0, "Voxel", [(i, j, k)])

                    results.extend(df.to_dict(orient="records"))

        return results

    # --------------------------------------------------

    def _run_mcmc(self, mrsi_fc, names, faxis, basis_array_FID, t, roi):

        x_range, y_range, z_range = self._get_ranges(mrsi_fc.spatial_shape, roi)
        P, M = basis_array_FID.shape
        results = []

        for x in x_range:
            for y in y_range:
                for z in z_range:

                    mrs = mrsi_fc.mrs_by_index([x, y, z])
                    mrs.rescaleForFitting()

                    if np.mean(mrs.FID) == 0:
                        continue

                    obs = mrs.get_spec()
                    obs = obs / np.max(np.abs(obs))
                    obs = polynomial_baseline_correction(faxis, obs)

                    initial_guess = np.zeros(M + 1)

                    output = minimize(
                        objective_function,
                        initial_guess,
                        args=(t, basis_array_FID, M, obs, 0, P),
                        method="TNC",
                        jac=grad
                    )

                    gamma_init = output.x[M]

                    A_mcmc_H, gamma, *_ = MCMC_ber_laplace_MH_within_Gibbs(
                        output.x[0:M],
                        gamma_init,
                        basis_array_FID,
                        obs,
                        4,
                        2,
                        t,
                        0,
                        0,
                        P
                    )

                    results.append({
                        "Voxel": (x, y, z),
                        "A_mcmc": A_mcmc_H.tolist(),
                        "gamma": float(gamma)
                    })

        return results