import numpy as np
import base64
from src.Modele.mrsi import MRSI
from src.logger import get_logger

logger = get_logger(__name__)

class METABOLITE_EXTRACTOR:
    """
    EN TRAVAUX, NE PAS UTILISER
    Extraction de métabolites voxel par voxel à partir d'une MRSI.
    Retourne des cartes 3D normalisées pour affichage front.
    """
    # Valeurs attendues (ppm) (valeurs obtenues diapo 2 ref )
    METABOLITES_VALEURS = { 
            "NAA": 2.01,
            "Cr": 3.02,
            "Cho": 3.22
    }
    
    # Largeur de bande d'intégration en ppm (comment choisir ???)
    INTEGRATION_WIDTH = 0.2

    def __init__(self, mrsi_instance: MRSI, irm_instance=None):
        self.mrsi = mrsi_instance
        self.irm = irm_instance
        if self.mrsi.data is None:
            self.mrsi.load()
            
        # Tenter de récupérer les infos spectrales du header si possible
        self.ppm_range = (10.0, -2.0) # convention décroissante souvent
    
    def ppm_to_index(self, ppm_value, T):
        """
        Convertit une valeur ppm en index T.
        """
        ppm_start, ppm_end = self.ppm_range
        fraction = (ppm_value - ppm_start) / (ppm_end - ppm_start)
        index = int(fraction * T)
        return max(0, min(T-1, index))

    def run(self, metabolites : list | None = None):
        """
        Extraction de métabolites choisis (entre NAA, Cr, Cho).
        """
        # Par défaut : tous
        if metabolites is None:
            metabolites = list(self.METABOLITES_VALEURS.keys())

        results = {}
        
        # Récup info dimensions
        if self.mrsi.data is None: 
             return {"error": "No data"}
             
        d = self.mrsi.data
        X, Y, Z, T = d.shape

        for name in metabolites:
            ppm_center = self.METABOLITES_VALEURS.get(name)

            if ppm_center is None:
                results[name] = {"error": f"metabolite inconnu : {name}"}
                continue
            
            # Calcul range indices
            ppm_min = ppm_center - (self.INTEGRATION_WIDTH / 2)
            ppm_max = ppm_center + (self.INTEGRATION_WIDTH / 2)
            
            idx_1 = self.ppm_to_index(ppm_min, T)
            idx_2 = self.ppm_to_index(ppm_max, T)
            
            start = min(idx_1, idx_2)
            end = max(idx_1, idx_2)
            
            if start == end:
                end += 1
            
            results[name] = self.extract_by_index_range((start, end))

        return results
    
    def _resample_to_mri(self, mrsi_3d_map):
        if self.irm is None or self.irm.img is None:
            return mrsi_3d_map, None, None

        logger.debug("Resampling MRSI to MRI grid (Bounding Box Strategy)...")
        
        # 1. MRI Grid Shape & Affine
        mri_shape = self.irm.data.shape
        mri_affine = self.irm.img.affine
        nx, ny, nz = mri_shape
        
        # 2. MRSI Shape & Affine
        mx, my, mz = mrsi_3d_map.shape
        mrsi_affine = self.mrsi.img.affine.copy()
        
        logger.debug(f"MRI Affine:\n{mri_affine}")
        logger.debug(f"Original MRSI Affine:\n{mrsi_affine}")
        
        # --- FALLBACK ALIGNMENT CHECK ---
        # Check if MRSI affine is Identity (often means missing registration)
        # We check the 3x3 scaling/rotation part and the translation part
        is_identity = np.allclose(mrsi_affine, np.eye(4), atol=1e-3)
        if is_identity:
            logger.warning("MRSI Affine is Identity! Attempting Fallback: Center Alignment with Header Scaling.")
            
            # 1. Apply Scaling from Header
            # Identity affine implies 1mm voxels. We must restore true voxel size.
            try:
                sx, sy, sz = self.mrsi.img.header.get_zooms()[:3]
                logger.info(f"Detected Voxel Size from Header: {sx:.2f} x {sy:.2f} x {sz:.2f} mm")
                
                # --- Dynamic Fit-to-Brain Strategy ---
                # Determine Brain Bounding Box from MRI Data
                logger.debug("Calculating Brain Bounding Box for Fit-to-Brain scaling...")
                mri_data = self.irm.data
                
                # Threshold to find brain (skip background)
                # Assuming modest signal intensity > 40.
                mask = mri_data > 40
                
                if np.any(mask):
                    # Fast projection to find bounds
                    x_any = np.any(mask, axis=(1, 2))
                    y_any = np.any(mask, axis=(0, 2))
                    z_any = np.any(mask, axis=(0, 1))
                    
                    x_min, x_max = np.where(x_any)[0][[0, -1]]
                    y_min, y_max = np.where(y_any)[0][[0, -1]]
                    z_min, z_max = np.where(z_any)[0][[0, -1]]
                    
                    # Brain dimensions in MRI indices
                    w_idx = x_max - x_min
                    h_idx = y_max - y_min
                    d_idx = z_max - z_min
                    
                    # Brain dimensions in mm (using MRI zooms)
                    # Note: mri_affine diagonal usually holds zooms, or header. 
                    # We can estimate scale from affine norm.
                    msx = np.linalg.norm(mri_affine[:3, 0])
                    msy = np.linalg.norm(mri_affine[:3, 1])
                    msz = np.linalg.norm(mri_affine[:3, 2])
                    
                    w_mm = w_idx * msx
                    h_mm = h_idx * msy
                    d_mm = d_idx * msz
                    
                    logger.info(f"Brain Dimensions detected: {w_mm:.1f} x {h_mm:.1f} x {d_mm:.1f} mm")
                    
                    # Target: MRSI ROI usually covers central 60-70% of brain
                    target_ratio = 0.65
                    
                    # MRSI Grid Dimensions
                    mx, my, mz = mrsi_3d_map.shape
                    
                    # Calculated necessary voxel size to fit target ratio
                    # size * mx = target_ratio * w_mm
                    # size = (target * w_mm) / mx
                    
                    vx = (target_ratio * w_mm) / mx
                    vy = (target_ratio * h_mm) / my
                    vz = (target_ratio * d_mm) / mz
                    
                    # To keep voxels cubic (square on screen), take the minimum or average?
                    # Usually spectroscopy voxels are roughly cubic.
                    # Let's take the minimum to ensure it fits inside the smallest brain dimension.
                    final_sz = min(vx, vy, vz)
                    
                    # Clamp to reasonable bounds (e.g. 5mm - 20mm)
                    final_sz = max(5.0, min(20.0, final_sz))
                    
                    logger.info(f"Dynamic Scaling: Forcing cubic voxel size {final_sz:.2f}mm to fit brain window.")
                    sx, sy, sz = final_sz, final_sz, final_sz
                else:
                    logger.warning("Could not detect brain signal (all < 40). Defaulting to 10mm.")
                    sx, sy, sz = 10.0, 10.0, 10.0
                
                # Apply to diagonal
                mrsi_affine[0, 0] = sx
                mrsi_affine[1, 1] = sy
                mrsi_affine[2, 2] = sz
            except Exception as e:
                logger.warning(f"Could not read zooms from header: {e}. Defaulting to 1mm.")

            # 2. Calculate MRI World Center
            # Center index
            c_mri_idx = np.array([nx/2, ny/2, nz/2, 1])
            c_mri_world = mri_affine @ c_mri_idx
            
            # 3. Calculate MRSI World Center (Current - now Scaled)
            c_mrsi_idx = np.array([mx/2, my/2, mz/2, 1])
            c_mrsi_world = mrsi_affine @ c_mrsi_idx
            
            # 4. Calculate Shift needed to align centers
            shift = c_mri_world - c_mrsi_world
            
            # 5. Apply Shift to MRSI Affine
            mrsi_affine[0, 3] += shift[0]
            mrsi_affine[1, 3] += shift[1]
            mrsi_affine[2, 3] += shift[2]
            
            logger.info(f"Corrected MRSI Affine with shift {shift[:3]}:\n{mrsi_affine}")
        
        # 3. Calculate Bounding Box of MRSI in MRI Index Space
        # Calculate Inverse MRI Affine
        try:
            inv_mri_affine = np.linalg.inv(mri_affine)
        except:
             logger.error("MRI affine not invertible")
             return mrsi_3d_map, None, None

        # Corners of MRSI (index space) -> (0,0,0) to (mx, my, mz)
        # Actually (mx-1)? No, the volume extent is 0 to mx.
        corners_mrsi = np.array([
            [0, 0, 0, 1],
            [mx, 0, 0, 1],
            [0, my, 0, 1],
            [mx, my, 0, 1],
            [0, 0, mz, 1],
            [mx, 0, mz, 1],
            [0, my, mz, 1],
            [mx, my, mz, 1]
        ]).T # 4x8

        # Transform to World: MRSI_Affine @ Corners
        corners_world = mrsi_affine @ corners_mrsi 
        
        # Transform to MRI Index: inv_MRI @ World
        corners_mri = inv_mri_affine @ corners_world
        
        # Calculate Box
        min_c = np.floor(corners_mri.min(axis=1)).astype(int)
        max_c = np.ceil(corners_mri.max(axis=1)).astype(int)
        
        v_min_x, v_min_y, v_min_z = min_c[0], min_c[1], min_c[2]
        v_max_x, v_max_y, v_max_z = max_c[0], max_c[1], max_c[2]

        logger.debug(f"Calculated MRSI Bounding Box in MRI Indices: X[{v_min_x}:{v_max_x}], Y[{v_min_y}:{v_max_y}], Z[{v_min_z}:{v_max_z}]")

        # Clamp to MRI dimensions
        start_x = max(0, v_min_x)
        end_x = min(nx, v_max_x)
        start_y = max(0, v_min_y)
        end_y = min(ny, v_max_y)
        start_z = max(0, v_min_z)
        end_z = min(nz, v_max_z)

        logger.debug(f"Clamped Sampling Box: X[{start_x}:{end_x}], Y[{start_y}:{end_y}], Z[{start_z}:{end_z}]")
        
        # Check if empty
        if start_x >= end_x or start_y >= end_y or start_z >= end_z:
            logger.warning("MRSI volume is completely outside MRI volume!")
            return np.zeros(mri_shape, dtype=np.float32), mri_shape, mri_affine

        # 4. Resampling Loop (Iterate only inside the box)
        resampled = np.zeros(mri_shape, dtype=np.float32)
        
        # Matrix M for MRI_Index -> MRSI_Index
        # inv_MRSI @ MRI
        try:
             inv_mrsi_affine = np.linalg.inv(mrsi_affine)
             M = inv_mrsi_affine @ mri_affine
        except:
             return mrsi_3d_map, None, None
            
        # Iterate over the Z range of the box
        for z in range(start_z, end_z):
            # Meshgrid for this slice limited to Y/X box
            # box width/height
            bx_w = end_x - start_x
            bx_h = end_y - start_y
            
            # coords relative to MRI volume (0-based or absolute?)
            # np.arange(start_x, end_x)
            xv, yv = np.meshgrid(np.arange(start_x, end_x), np.arange(start_y, end_y), indexing='ij')
            
            # Map pixels to MRSI index
            u = M[0,0]*xv + M[0,1]*yv + M[0,2]*z + M[0,3]
            v = M[1,0]*xv + M[1,1]*yv + M[1,2]*z + M[1,3]
            w = M[2,0]*xv + M[2,1]*yv + M[2,2]*z + M[2,3]
            
            u_i = np.rint(u).astype(int)
            v_i = np.rint(v).astype(int)
            w_i = np.rint(w).astype(int)
            
            valid = (u_i >= 0) & (u_i < mx) & (v_i >= 0) & (v_i < my) & (w_i >= 0) & (w_i < mz)
            
            # Insert into the full slice
            # resampled[z] is (nx, ny). We only update [start_x:end_x, start_y:end_y]
            
            if np.any(valid):
                # Extract valid values from mrsi map
                values = mrsi_3d_map[u_i[valid], v_i[valid], w_i[valid]]
                
                # Create a mini-mask for the subregion
                # region_slice.shape is (bx_w, bx_h)
                region_slice = np.zeros((bx_w, bx_h), dtype=np.float32)
                region_slice[valid] = values
                
                # Place into full array
                resampled[start_x:end_x, start_y:end_y, z] = region_slice

        return resampled, mri_shape, mri_affine

    def extract_by_index_range(self, freq_range: tuple):
        """
        Extrait la carte 3D pour une plage d'indices donnée.
        """
        d = self.mrsi.data  # shape (X,Y,Z,T)
        X, Y, Z, T = d.shape
        min_idx, max_idx = freq_range

        min_idx = max(0, min_idx)
        max_idx = min(T, max_idx)

        if min_idx >= max_idx:
             voxel_map = np.zeros((X,Y,Z))
        else:
             voxel_map = np.sum(np.abs(d[:, :, :, min_idx:max_idx]), axis=-1)

        # Normalisation [0-255]
        vmin, vmax = voxel_map.min(), voxel_map.max()
        if vmin == vmax:
            norm_voxel_map = np.zeros_like(voxel_map, dtype=np.float32)
        else:
            norm_voxel_map = ((voxel_map - vmin) / (vmax - vmin) * 255)

        # RESAMPLING if MRI provided
        used_shape = [int(X), int(Y), int(Z)]
        affine_to_send = self.mrsi.img.affine
        
        if self.irm:
             norm_voxel_map, mri_shape, mri_affine = self._resample_to_mri(norm_voxel_map)
             used_shape = [int(s) for s in mri_shape]
             affine_to_send = mri_affine  # Use MRI affine since data is now in MRI grid

        # Convert to uint8 for transport
        final_map = norm_voxel_map.astype(np.uint8)

        return {
            "type": "MRSI",
            "type_traitement" : "metabolite_extractor",
            "nom": f"{self._basename_no_ext(self.mrsi.nom)}_metabolite",
            "data_b64": base64.b64encode(final_map.tobytes()).decode('utf-8'),
            "shape": used_shape,
            "method": f"metabolite_idx_{min_idx}_{max_idx}_resampled_{self.irm is not None}",
            "affine": [ [float(v) for v in row] for row in affine_to_send ] if affine_to_send is not None else None,
            "spacing": [float(x) for x in self.mrsi.img.header.get_zooms()[:3]] if self.mrsi.img is not None else None
        }

    def _basename_no_ext(self, filename: str) -> str:
        if filename.endswith(".nii.gz"):
            return filename[:-7]
        elif filename.endswith(".nii"):
            return filename[:-4]
        else:
            return filename
