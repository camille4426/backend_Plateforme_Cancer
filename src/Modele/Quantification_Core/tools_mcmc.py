from scipy.optimize import curve_fit
import numpy as np
from fsl_mrs.core.nifti_mrs import NIFTI_MRS
from fsl_mrs.utils.misc import SpecToFID
from nifti_mrs import create_nmrs


def align_mrsi_spectra(mrsi_data, names, basis_array_spec, ppm) :
    size_x, size_y, size_z = mrsi_data.spatial_shape
    mrsi_array_align = np.zeros([mrsi_data.spatial_shape[0], mrsi_data.spatial_shape[1], mrsi_data.spatial_shape[2], mrsi_data.FID_points], dtype=complex)
    for x in range(size_x) :
        for y in range(size_y) :
            for z in range(size_z) :
                obs = mrsi_data.mrs_by_index([x, y, z]).get_spec()
                I_max = np.argmax(np.real(obs))
                # Initialize Metab_H
                Metab_H = None

                if 1.8 <= ppm[I_max] <= 2.2:  # NAA
                    Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'NAA')])
                    # print('realigned on NAA')
                elif 3.1 <= ppm[I_max] <= 3.6:  # Cr
                    Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'PCh')])
                    # print('realigned on PCh')
                elif 2.8 <= ppm[I_max] <= 3.1:  # Cho
                    Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'Cr')])
                    # print('realigned on Cr')
                elif 1.3 <= ppm[I_max] <= 1.4:
                    print(f'High Lipid/lactate contamination possible for voxel [{x},{y},{z}]')
                else:
                    pass
                    # print('No shift correction, unable to recognise main metabolites')

                # Proceed only if Metab_H was set
                if Metab_H is not None:
                    I_metab = np.argmax(Metab_H)
                    shift = I_metab - I_max
                    obs = np.roll(obs, shift )

                mrsi_array_align[x, y, z] = SpecToFID(obs) #np.fft.ifft(np.fft.ifftshift(obs, axis=0), axes=0)

    return NIFTI_MRS(create_nmrs.gen_nifti_mrs(mrsi_array_align, 1/mrsi_data.header['bandwidth'], mrsi_data.header['centralFrequency']), header=mrsi_data.header) 





def align_mrs_spectra(mrs_data, names, basis_array_spec, ppm) :
    obs = mrs_data
    I_max = np.argmax(np.real(obs))
    # Initialize Metab_H
    Metab_H = None

    if 1.8 <= ppm[I_max] <= 2.2:  # NAA
        Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'NAA')])
        print('realigned on NAA')
    elif 3.1 <= ppm[I_max] <= 3.6:  # Cr
        Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'PCh')])
        # print('realigned on PCh')
    elif 2.8 <= ppm[I_max] <= 3.1:  # Cho
        Metab_H = np.real(basis_array_spec[:, np.where(np.array(names) == 'Cr')])
        # print('realigned on Cr')
    # elif 1.3 <= ppm[I_max] <= 1.4:
    #     print(f'High Lipid/lactate contamination possible for this voxel')
    else:
        pass
        # print('No shift correction, unable to recognise main metabolites')

    # Proceed only if Metab_H was set
    if Metab_H is not None:
        I_metab = np.argmax(Metab_H)
        shift = I_metab - I_max
        print(f'I_metab = {I_metab}')
        print(f'I_max = {I_max}')
        obs = np.roll(obs, shift )


    return obs, shift

def excludedata(ppm, y, indices):
    mask = np.ones(len(ppm), dtype=bool)
    mask[indices] = False
    return mask

def polynomial_fit(ppm, y, degree, exclude_mask):
    def poly_func(x, *params):
        return np.polyval(params, x)
    
    params, _ = curve_fit(poly_func, ppm[exclude_mask], y[exclude_mask], p0=[0]*degree)
    return lambda x: poly_func(x, *params)

def polynomial_baseline_correction(ppm, y):
    x1 = np.where((ppm > 0.7) & (ppm < 1.1))[0]
    x2 = np.where((ppm > 1.2) & (ppm < 1.6))[0]
    x3 = np.where((ppm > 1.9) & (ppm < 2.1))[0]
    x4 = np.where((ppm > 2.9) & (ppm < 3.35))[0]
    x5 = np.where((ppm > 3.5) & (ppm < 4))[0]
    
    x = np.concatenate((x1, x2, x3, x4, x5))

    exclude_re = excludedata(ppm, np.real(y), x)
    exclude_im = excludedata(ppm, np.imag(y), x)

    cfun_re = polynomial_fit(ppm, np.real(y), degree=3, exclude_mask=exclude_re)
    cfun_im = polynomial_fit(ppm, np.imag(y), degree=3, exclude_mask=exclude_im)

    baseline_re = cfun_re(ppm)
    baseline_im = cfun_im(ppm)

    corrected_signal = y - baseline_re - 1j * baseline_im
    return corrected_signal