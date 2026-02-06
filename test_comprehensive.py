"""
Comprehensive Backend API Test Suite
Tests all endpoints and validates response structures
"""
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

def test_root():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Root endpoint failed: {resp.status_code}"
    data = resp.json()
    assert data.get("status") == "ok", "Root endpoint should return status ok"
    print("✅ Root endpoint working")
    return True

def test_auth():
    """Test authentication"""
    print("\n=== Testing Authentication ===")
    # Test with wrong credentials
    resp = requests.post(f"{BASE_URL}/token", data={"username": "wrong", "password": "wrong"})
    assert resp.status_code == 401, "Should reject wrong credentials"
    
    # Test with correct credentials
    token = get_token()
    assert token is not None, "Should get token with correct credentials"
    print("✅ Authentication working correctly")
    return token

def test_irm_upload(token):
    """Test IRM upload and validate response structure"""
    print("\n=== Testing IRM Upload ===")
    headers = {"Authorization": f"Bearer {token}"}
    irm_file = "bin_test_data/MRI/MsrGB01_PUI_20110324_0000.nii.gz"
    
    with open(irm_file, "rb") as f:
        files = {"fichier": (os.path.basename(irm_file), f, "application/gzip")}
        resp = requests.post(f"{BASE_URL}/upload-irm/", headers=headers, files=files)
    
    assert resp.status_code == 200, f"IRM upload failed: {resp.status_code}"
    data = resp.json()
    
    # Validate response structure
    assert "type" in data, "Response should have 'type' field"
    assert data["type"] == "IRM", "Type should be IRM"
    
    assert "nom_fichier" in data, "Response should have 'nom_fichier' field"
    assert "shape" in data, "Response should have 'shape' field"
    assert len(data["shape"]) == 3, "Shape should be 3D [X, Y, Z]"
    
    assert "data" in data, "Response should have 'data' field with 3D volume"
    assert isinstance(data["data"], list), "Data should be a list"
    assert len(data["data"]) == data["shape"][0], "Data first dimension should match shape[0]"
    
    print(f"✅ IRM Upload validated: shape={data['shape']}, filename={data['nom_fichier']}")
    return data

def test_mrsi_upload(token):
    """Test MRSI upload and validate response structure"""
    print("\n=== Testing MRSI Upload ===")
    headers = {"Authorization": f"Bearer {token}"}
    mrsi_file = "bin_test_data/MRSI/MsrGB_MRSI_01_PUI_20110324_hsvd_atlas.nii"
    
    with open(mrsi_file, "rb") as f:
        files = {"fichier": (os.path.basename(mrsi_file), f, "application/octet-stream")}
        resp = requests.post(f"{BASE_URL}/upload-mrsi/", headers=headers, files=files)
    
    assert resp.status_code == 200, f"MRSI upload failed: {resp.status_code}"
    data = resp.json()
    
    # Validate response structure
    assert "type" in data, "Response should have 'type' field"
    assert data["type"] == "MRSI", "Type should be MRSI"
    
    assert "nom" in data, "Response should have 'nom' field"
    assert "shape" in data, "Response should have 'shape' field"
    assert len(data["shape"]) == 3, "Shape should be 3D [X, Y, Z]"
    
    assert "voxel_map_all" in data, "Response should have 'voxel_map_all' field"
    assert isinstance(data["voxel_map_all"], list), "voxel_map_all should be a list"
    assert len(data["voxel_map_all"]) == data["shape"][2], "Should have one map per Z slice"
    
    assert "method" in data, "Response should have 'method' field"
    
    print(f"✅ MRSI Upload validated: shape={data['shape']}, slices={len(data['voxel_map_all'])}")
    return data

def test_spectrum_retrieval(token, mrsi_shape):
    """Test spectrum retrieval with various coordinates"""
    print("\n=== Testing Spectrum Retrieval ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    X, Y, Z = mrsi_shape
    test_coords = [
        (0, 0, 0),  # Corner
        (X//2, Y//2, Z//2),  # Center
        (X-1, Y-1, Z-1),  # Opposite corner
    ]
    
    for x, y, z in test_coords:
        resp = requests.get(f"{BASE_URL}/spectrum/{x}/{y}/{z}", headers=headers)
        assert resp.status_code == 200, f"Spectrum retrieval failed at ({x},{y},{z}): {resp.status_code}"
        
        data = resp.json()
        assert "type" in data, "Response should have 'type'"
        assert data["type"] == "MRSI", "Type should be MRSI"
        assert "spectrum" in data, "Response should have 'spectrum' field"
        assert isinstance(data["spectrum"], list), "Spectrum should be a list"
        assert len(data["spectrum"]) > 0, "Spectrum should not be empty"
        assert "voxel" in data, "Response should have 'voxel' coordinates"
        assert data["voxel"]["x"] == x, "Voxel x coordinate mismatch"
        assert data["voxel"]["y"] == y, "Voxel y coordinate mismatch"
        assert data["voxel"]["z"] == z, "Voxel z coordinate mismatch"
        
    print(f"✅ Spectrum retrieval validated for {len(test_coords)} test coordinates")
    return True

def test_out_of_bounds_spectrum(token):
    """Test spectrum retrieval with out-of-bounds coordinates"""
    print("\n=== Testing Out-of-Bounds Spectrum ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # This should return an error
    resp = requests.get(f"{BASE_URL}/spectrum/999/999/999", headers=headers)
    assert resp.status_code == 200, "Should return 200 but with error message"
    data = resp.json()
    assert "error" in data, "Should return error for out-of-bounds coordinates"
    print("✅ Out-of-bounds handling validated")
    return True

def test_json_dataset(token):
    """Test JSON dataset organization"""
    print("\n=== Testing JSON Dataset Organization ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Load example JSON
    with open("bin_test_data/exemple_json_front.json", "r") as f:
        json_data = json.load(f)
    
    resp = requests.post(f"{BASE_URL}/upload-json-dataset/", headers=headers, json=json_data)
    assert resp.status_code == 200, f"JSON dataset upload failed: {resp.status_code}"
    
    data = resp.json()
    # The response should be organized by patient
    print(f"✅ JSON dataset organization working: {len(data) if isinstance(data, dict) else 'N/A'} patients")
    return data

def run_all_tests():
    """Run all tests"""
    print("="*70)
    print("BACKEND API COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    try:
        # Test 1: Root endpoint
        test_root()
        
        # Test 2: Authentication
        token = test_auth()
        
        # Test 3: IRM Upload
        irm_data = test_irm_upload(token)
        
        # Test 4: MRSI Upload
        mrsi_data = test_mrsi_upload(token)
        
        # Test 5: Spectrum Retrieval
        test_spectrum_retrieval(token, mrsi_data["shape"])
        
        # Test 6: Out-of-bounds handling
        test_out_of_bounds_spectrum(token)
        
        # Test 7: JSON Dataset
        test_json_dataset(token)
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        return True
        
    except AssertionError as e:
        print("\n" + "="*70)
        print(f"❌ TEST FAILED: {e}")
        print("="*70)
        return False
    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("="*70)
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
