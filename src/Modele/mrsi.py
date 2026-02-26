import os
import tempfile
import base64
import numpy as np
import nibabel as nib
from fastapi import UploadFile
import scipy.ndimage
from src.logger import get_logger

logger = get_logger(__name__)

class MRSI:
    """
    Classe pour fichiers MRSI (.nii).
    Objectif:
      - renvoyer une "carte voxels" (résumé d'intensité)
      - renvoyer un spectre pour un voxel donné
    """

    def __init__(self, nom: str, fichier: UploadFile):
        self.nom = nom
        self.fichier = fichier
        self.img = None
        self.data = None  # numpy array

    def _save_upload_to_temp(self) -> str:
        suffix = ".nii"
        if self.fichier.filename and self.fichier.filename.lower().endswith(".nii.gz"):
            suffix = ".nii.gz"

        try:
            self.fichier.file.seek(0)
        except Exception:
            pass

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(self.fichier.file.read())
            return tmp.name

    def load(self):
        tmp_path = self._save_upload_to_temp()
        try:
            self.img = nib.load(tmp_path)

            data = self.img.get_fdata(dtype=np.complex64)

            if not np.iscomplexobj(data):
                data = np.asanyarray(self.img.dataobj)

            self.data = data

            logger.info(
                f"MRSI chargée: shape={self.data.shape}, dtype={self.data.dtype}"
            )

        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def _to_uint8_slice(self, sl: np.ndarray) -> np.ndarray:
        """
        Normalise une coupe 2D en uint8 [0..255].
        """
        sl = np.asarray(sl, dtype=np.float32)
        vmin, vmax = np.nanmin(sl), np.nanmax(sl)
        if vmin == vmax:
            return np.zeros_like(sl, dtype=np.uint8)
        out = (sl - vmin) / (vmax - vmin)
        return (out * 255).astype(np.uint8)

    def voxel_map(self, z=None, method="sum_abs"):
        """
        Construit une carte MRSI à partir des spectres.

        - data shape attendue: (16,16,8,512)
        - z optionnel: renvoie une coupe 2D (16x16)
        """

        if self.data is None:
            self.load()

        d = self.data

        if d.ndim != 4:
            return {
                "error": f"MRSI attendue en 4D (X,Y,Z,T). Reçu ndim={d.ndim}",
                "shape": list(d.shape),
            }

        # ---- Calcul voxel map 3D ----
        if method == "max_abs":
            vm = np.max(np.abs(d), axis=-1)   # (16,16,8)
        elif method == "sum":
            vm = np.sum(d, axis=-1)
        else:  # sum_abs par défaut
            vm = np.sum(np.abs(d), axis=-1)

        # ---- Si on veut une coupe 2D ----
        if z is not None:
            z = int(z)
            vm2d = vm[:, :, z]   # (16,16)
            vm2d_norm = self._to_uint8_slice(vm2d)
            return {
                "type": "MRSI",
                "nom": self.nom,
                "z": z,
                "voxel_map_2d": vm2d_norm.tolist(),
                "shape": list(vm2d.shape),
                "method": method
            }

    def get_all_voxel_maps(self, method="sum_abs"):
        """
        Renvoie TOUTES les coupes de la voxel map.
        """
        if self.data is None:
            self.load()
        
        d = self.data
        if d.ndim != 4:
            return {"error": "MRSI non 4D"}

        if method == "max_abs":
            vm = np.max(np.abs(d), axis=-1)
        elif method == "sum":
            vm = np.sum(d, axis=-1)
        else:
            vm = np.sum(np.abs(d), axis=-1)

        X, Y, Z = vm.shape
        
        # Normalize to 0-255 range
        vm = np.asarray(vm, dtype=np.float32)
        vmin, vmax = np.nanmin(vm), np.nanmax(vm)
        if vmin == vmax:
             vm_norm = np.zeros_like(vm, dtype=np.uint8)
        else:
             vm_norm = ((vm - vmin) / (vmax - vmin) * 255).astype(np.uint8)

        return {
            "type": "MRSI",
            "nom": self.nom,
            "data_b64": base64.b64encode(vm_norm.tobytes()).decode('utf-8'),
            "shape": [int(X), int(Y), int(Z)],
            "method": method,
            "affine": [ [float(v) for v in row] for row in self.img.affine ] if self.img is not None else None,
            "spacing": [float(x) for x in self.img.header.get_zooms()[:3]] if self.img is not None else None
        }


    def get_spectrum(self, x: int, y: int, z: int):
        """
        Renvoie le spectre 1D du voxel (x,y,z).
        """
        return self.spectrum(x, y, z)
"""
    def spectrum(self, x: int, y: int, z: int):
        """
        Renvoie le spectre 1D du voxel (x,y,z) si data est 4D (X,Y,Z,T).
        """
        if self.data is None:
            self.load()
        if self.data is None:
            return {"error": "Impossible de charger la MRSI"}

        d = self.data
        if d.ndim != 4:
            return {"error": f"Spectre voxel nécessite une MRSI 4D (X,Y,Z,T). Reçu ndim={d.ndim}", "shape": list(d.shape)}

        X, Y, Z, T = d.shape
        if not (0 <= x < X and 0 <= y < Y and 0 <= z < Z):
            return {"error": "Indices voxel hors limites", "shape": [int(X), int(Y), int(Z), int(T)]}

        sp = d[int(x), int(y), int(z), :]
        # JSON-friendly
        return {
            "type": "MRSI",
            "nom": self.nom,
            "voxel": {"x": int(x), "y": int(y), "z": int(z)},
            "T": int(T),
            "spectrum": sp.tolist(),
        }
        """
    def spectrum(self, x: int, y: int, z: int):

        if self.data is None:
            self.load()

        d = self.data
        X, Y, Z, T = d.shape

        sp = d[int(x), int(y), int(z), :]

        if np.iscomplexobj(sp):
            real = np.real(sp)
            imag = np.imag(sp)
            magnitude = np.abs(sp)
        else:
            real = sp
            imag = np.zeros_like(sp)
            magnitude = sp

        return {
            "type": "MRSI",
            "nom": self.nom,
            "voxel": {"x": int(x), "y": int(y), "z": int(z)},
            "T": int(T),

            # 🔹 Backward compatible
            "spectrum": magnitude.tolist(),

            # 🔹 Proper complex support
            "real": real.tolist(),
            "imag": imag.tolist()
        }
        

    def summary(self):
        shape = self.data.shape if self.data is not None else None
        return {"type": "MRSI", "nom": self.nom, "shape": shape}

    def resample_to_mri(self, mri_shape, mri_affine, force_center=False, channel=None):
        """
        Resample the MRSI data to match the MRI's shape and affine.
        Handles missing/identity MRSI affine using a 'Center-to-Center' heuristic.
        
        Args:
            mri_shape: (X, Y, Z) tuple of the target MRI.
            mri_affine: 4x4 numpy array of the target MRI.
            force_center: If True, forces the Center-to-Center heuristic even if MRSI affine looks valid.
            channel: If int, selects that channel. If None, uses sum of abs.
            
        Returns:
            (resampled_data, transform_matrix) tuple.
            transform_matrix is the 4x4 matrix mapping MRI voxel indices -> MRSI voxel indices.
        """
        if self.data is None:
            self.load()
            
        d = self.data
        if d.ndim == 4:
             # Reduce to 3D
             if channel is not None and isinstance(channel, int):
                 if 0 <= channel < d.shape[3]:
                      d = d[..., channel]
                 else:
                      # Fallback if index out of bound
                      logger.warning(f"resample_to_mri: channel {channel} out of bounds (max {d.shape[3]-1}). using sum_abs.")
                      d = np.sum(np.abs(d), axis=-1)
             else:
                 # Default mix
                 d = np.sum(np.abs(d), axis=-1)
             
        # Normalize to 0-1 for visualization before interpolation, or keep raw?
        # Let's keep raw values for now, frontend can handle normalization/colormap
        
        mrsi_affine = self.img.affine
        
        # Check if we need to use the Fallback Heuristic
        # Heuristic trigger: force_center is True OR affine is Identity OR Translation is zero
        is_identity = np.allclose(mrsi_affine, np.eye(4))
        translation = mrsi_affine[:3, 3]
        is_zero_translation = np.allclose(translation, [0, 0, 0])
        
        if force_center or is_identity or is_zero_translation:
            logger.info(f"Fusion: Triggering Center-to-Center Fallback (force={force_center}, ident={is_identity}, zero_trans={is_zero_translation})")
            
            # --- Step A: Get MRI Physical Center ---
            # Center_vox = (Shape - 1) / 2  ? Or Shape / 2 ? 
            # Physical center = affine * [dim/2, dim/2, dim/2, 1]
            # Let's use the simple formula from the request:
            # Center_mri = (Shape_mri * VoxelSize_mri) / 2 + Origin_mri
            
            mri_zoom = np.sqrt(np.sum(mri_affine[:3, :3]**2, axis=0))
            mri_origin = mri_affine[:3, 3]
            mri_phys_types_center = (np.array(mri_shape) * mri_zoom) / 2 + mri_origin
            
            # Alternative (more robust): Calculate the physical coordinate of the center voxel
            # center_idx = np.array(mri_shape) / 2.0
            # mri_phys_center = mri_affine.dot(np.append(center_idx, 1))[:3]
            
            # Let's stick to the request's logic which seems to imply aligning physical bounding boxes centers
            # But "Shape * VoxelSize / 2 + Origin" is exactly the physical center of the volume 
            # IF the axes are aligned. If there's rotation, it's safer to use the affine.
            
            # Using the affine to get the center physical coordinate:
            cx, cy, cz = np.array(mri_shape) / 2.0
            mri_center_phys = mri_affine @ [cx, cy, cz, 1.0]
            mri_center_phys = mri_center_phys[:3]

            # --- Step B: Get MRSI Physical Dimensions ---
            mrsi_shape = d.shape
            # If VoxelSize missing (implied by identity affine), assume 10mm isotropic
            # MRSI often has large voxels. User requested 6mm.
            mrsi_zoom = [6.0, 6.0, 6.0] 
            
            # If the MRSI affine was NOT identity but just had zero translation, we might trust the zoom
            # But if it is identity, zoom is 1.0. 
            # Let's check header zooms if available
            if self.img.header is not None:
                header_zooms = self.img.header.get_zooms()[:3]
                # If header zooms are notably different from 1.0 (defaults), use them.
                # Otherwise stick to 10.0 assumption for synthetic/bad data
                if not np.allclose(header_zooms, [1.0, 1.0, 1.0]):
                    mrsi_zoom = header_zooms
            
            mrsi_real_size = np.array(mrsi_shape) * np.array(mrsi_zoom)
            
            # --- Step C: Compute Translation Vector ---
            # We want the MRSI box centered on the MRI center
            # The top-left corner of MRSI (its new origin) should be:
            # Origin_new = MRI_Center - (MRSI_Size / 2)
            new_origin = mri_center_phys - (mrsi_real_size / 2.0)
            
            # --- Step D: Construct New Affine ---
            # Rotation/Scaling is just diagonal scaling (assuming no rotation for MRSI)
            new_affine = np.eye(4)
            new_affine[0,0] = mrsi_zoom[0]
            new_affine[1,1] = mrsi_zoom[1]
            new_affine[2,2] = mrsi_zoom[2]
            new_affine[:3, 3] = new_origin
            
            logger.info(f"Fusion: Calculated Fallback Affine: \n{new_affine}")
            mrsi_affine = new_affine

        # 3. Standard Modeling (Interpolation)
        # We need to map coordinates from Target (MRI) to Source (MRSI)
        # inv_mrsi_affine * mri_affine gives the mapping from MRI voxels to MRSI voxels
        
        inv_mrsi_affine = np.linalg.inv(mrsi_affine)
        fusion_matrix = inv_mrsi_affine @ mri_affine
        
        # scipy.ndimage.affine_transform applies the INVERSE of the matrix provided 
        # (it maps output->input). 
        # But we computed MRI(vox) -> MRSI(vox) directly.
        # So we pass the matrix directly?
        # Documentation: "The matrix M maps the output coordinates to the input coordinates."
        # Our output is the Resampled MRSI (which has MRI coordinates).
        # Our input is the Raw MRSI.
        # So we need a matrix that takes an MRI voxel (output) and gives an MRSI voxel (input).
        # that is exactly `inv_mrsi_affine @ mri_affine`.
        
        # affine_transform expects the top-left 3x3 as 'matrix' and translation as 'offset'
        # or a 4x4 (since scipy 0.18 ?? No, typically takes matrix and offset separately or a homogeneous matrix in recent versions?)
        # Let's verify standard usage. 
        # It's usually `affine_transform(input, matrix, offset, output_shape, ...)`
        # Where x_in = matrix @ x_out + offset
        
        # fusion_matrix is 4x4.
        M = fusion_matrix[:3, :3]
        offset = fusion_matrix[:3, 3]
        
        resampled = scipy.ndimage.affine_transform(
            d,
            matrix=M,
            offset=offset,
            output_shape=mri_shape,
            order=1, # Linear interpolation
            mode='constant',
            cval=0.0
        )
        
        # fusion_matrix maps MRI(vox) -> MRSI(vox)
        # We return it so frontend can map clicks
        return resampled, fusion_matrix
