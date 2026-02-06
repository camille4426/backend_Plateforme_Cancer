import requests
import json
import sys
import os

BASE_URL = "http://127.0.0.1:8000"

def get_token():
    """Get authentication token"""
    resp = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin"})
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

def test_upload_irm(token):
    """Test IRM file upload"""
    print("\n=== Testing IRM Upload ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with a sample IRM file
    irm_file = "bin_test_data/MRI/MsrGB01_PUI_20110324_0000.nii.gz"
    
    if not os.path.exists(irm_file):
        print(f"❌ Test file not found: {irm_file}")
        return None
        
    with open(irm_file, "rb") as f:
        files = {"fichier": (os.path.basename(irm_file), f, "application/gzip")}
        resp = requests.post(f"{BASE_URL}/upload-irm/", headers=headers, files=files)
        
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ IRM Upload Successful")
        print(f"Response keys: {list(data.keys())}")
        print(f"Type: {data.get('type')}")
        print(f"Filename: {data.get('nom_fichier')}")
        print(f"Shape: {data.get('shape')}")
        
        # Check if data is present
        if 'data' in data:
            print(f"✅ Data field present (3D volume)")
            print(f"   Data structure: nested list with {len(data['data'])} elements")
        else:
            print(f"❌ Data field NOT present")
            
        return data
    else:
        print(f"❌ IRM Upload Failed: {resp.text[:500]}")
        return None

def test_upload_mrsi(token):
    """Test MRSI file upload"""
    print("\n=== Testing MRSI Upload ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test with a sample MRSI file
    mrsi_file = "bin_test_data/MRSI/MsrGB_MRSI_01_PUI_20110324_hsvd_atlas.nii"
    
    if not os.path.exists(mrsi_file):
        print(f"❌ Test file not found: {mrsi_file}")
        return None
        
    with open(mrsi_file, "rb") as f:
        files = {"fichier": (os.path.basename(mrsi_file), f, "application/octet-stream")}
        resp = requests.post(f"{BASE_URL}/upload-mrsi/", headers=headers, files=files)
        
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ MRSI Upload Successful")
        print(f"Response keys: {list(data.keys())}")
        print(f"Type: {data.get('type')}")
        print(f"Name: {data.get('nom')}")
        print(f"Shape: {data.get('shape')}")
        
        # Check voxel maps
        if 'voxel_map_all' in data:
            print(f"✅ voxel_map_all present with {len(data['voxel_map_all'])} slices")
        else:
            print(f"❌ voxel_map_all NOT present")
            
        return data
    else:
        print(f"❌ MRSI Upload Failed: {resp.text[:500]}")
        return None

def test_spectrum(token):
    """Test getting spectrum from MRSI"""
    print("\n=== Testing Spectrum Retrieval ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(f"{BASE_URL}/spectrum/8/8/4", headers=headers)
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Spectrum Retrieved")
        print(f"Response keys: {list(data.keys())}")
        if 'spectrum' in data:
            print(f"   Spectrum length: {len(data['spectrum'])}")
        return data
    else:
        print(f"❌ Spectrum retrieval failed: {resp.text[:200]}")
        return None

if __name__ == "__main__":
    print("Testing Backend Uploads and Responses...")
    
    # Get token
    print("\n[1] Getting authentication token...")
    token = get_token()
    if not token:
        print("❌ Failed to get token")
        sys.exit(1)
    print(f"✅ Got token: {token[:20]}...")
    
    # Test IRM upload
    irm_data = test_upload_irm(token)
    
    # Test MRSI upload
    mrsi_data = test_upload_mrsi(token)
    
    # Test spectrum retrieval
    spectrum_data = test_spectrum(token)
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    
    print(f"IRM Upload: {'✅ SUCCESS' if irm_data else '❌ FAILED'}")
    print(f"MRSI Upload: {'✅ SUCCESS' if mrsi_data else '❌ FAILED'}")
    print(f"Spectrum Retrieval: {'✅ SUCCESS' if spectrum_data else '❌ FAILED'}")
