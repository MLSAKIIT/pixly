"""
Test suite for the enhanced screenshot system
Run with: python test_screenshots.py
"""

import requests
import base64
import time
from PIL import Image
import io

BASE_URL = "http://127.0.0.1:8000"

def test_api_key_configuration():
    """Test 1: API Key Configuration"""
    print("\n=== Test 1: API Key Configuration ===")
    
    # Check current status
    response = requests.get(f"{BASE_URL}/settings/api-key")
    print(f"API Key Status: {response.json()}")
    
    # Note: Uncomment and add your key to test saving
    # test_key = "your-test-api-key"
    # response = requests.post(
    #     f"{BASE_URL}/settings/api-key",
    #     json={"api_key": test_key}
    # )
    # print(f"Save Result: {response.json()}")
    
    print("✓ API Key test completed")

def test_screenshot_capture():
    """Test 2: Screenshot Capture System"""
    print("\n=== Test 2: Screenshot Capture ===")
    
    # Start capture with 10-second interval
    response = requests.post(
        f"{BASE_URL}/screenshots/start",
        params={"interval": 10, "auto_analyze": True}
    )
    print(f"Start Capture: {response.json()}")
    
    # Wait for a few captures
    print("Waiting 25 seconds for captures...")
    time.sleep(25)
    
    # Get recent screenshots
    response = requests.get(
        f"{BASE_URL}/screenshots/recent",
        params={"limit": 5}
    )
    data = response.json()
    print(f"Recent Screenshots: {data}")
    
    # Stop capture
    response = requests.post(f"{BASE_URL}/screenshots/stop")
    print(f"Stop Capture: {response.json()}")
    
    print("✓ Screenshot capture test completed")

def test_screenshot_retrieval():
    """Test 3: Screenshot Retrieval"""
    print("\n=== Test 3: Screenshot Retrieval ===")
    
    # Get recent screenshots
    response = requests.get(
        f"{BASE_URL}/screenshots/recent",
        params={"limit": 1}
    )
    screenshots = response.json()['screenshots']
    
    if not screenshots:
        print("⚠ No screenshots available. Skipping retrieval test.")
        return
    
    screenshot_id = screenshots[0][0]
    print(f"Testing with screenshot ID: {screenshot_id}")
    
    # Retrieve specific screenshot
    response = requests.get(f"{BASE_URL}/screenshots/{screenshot_id}")
    data = response.json()
    
    print(f"Retrieved screenshot: ID={data['metadata']['id']}, "
          f"App={data['metadata']['application']}")
    
    # Verify image data
    try:
        img_data = base64.b64decode(data['data'])
        image = Image.open(io.BytesIO(img_data))
        print(f"Image size: {image.size}")
        print("✓ Screenshot retrieval test completed")
    except Exception as e:
        print(f"✗ Error verifying image: {e}")

def test_screenshot_deletion():
    """Test 4: Screenshot Deletion"""
    print("\n=== Test 4: Screenshot Deletion ===")
    
    # Get a screenshot to delete
    response = requests.get(
        f"{BASE_URL}/screenshots/recent",
        params={"limit": 1}
    )
    screenshots = response.json()['screenshots']
    
    if not screenshots:
        print("⚠ No screenshots available. Skipping deletion test.")
        return
    
    screenshot_id = screenshots[0][0]
    print(f"Deleting screenshot ID: {screenshot_id}")
    
    # Delete
    response = requests.delete(f"{BASE_URL}/screenshots/{screenshot_id}")
    print(f"Delete Result: {response.json()}")
    
    # Verify deletion
    response = requests.get(f"{BASE_URL}/screenshots/{screenshot_id}")
    if response.status_code == 404:
        print("✓ Screenshot deletion test completed")
    else:
        print("✗ Screenshot was not deleted properly")

def test_chat_with_screenshot():
    """Test 5: Chat with Screenshot Analysis"""
    print("\n=== Test 5: Chat with Screenshot ===")
    
    # Get a recent screenshot
    response = requests.get(
        f"{BASE_URL}/screenshots/recent",
        params={"limit": 1}
    )
    screenshots = response.json()['screenshots']
    
    if not screenshots:
        print("⚠ No screenshots available. Skipping chat test.")
        return
    
    screenshot_id = screenshots[0][0]
    
    # Get screenshot data
    response = requests.get(f"{BASE_URL}/screenshots/{screenshot_id}")
    image_data = response.json()['data']
    
    # Send chat request with image
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "message": "What do you see in this screenshot? Provide gaming advice.",
            "image_data": image_data
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"AI Response: {result['response'][:200]}...")
        print(f"Game Detected: {result.get('game_detected', 'None')}")
        print("✓ Chat with screenshot test completed")
    else:
        print(f"✗ Chat failed: {response.status_code}")

def test_chat_without_screenshot():
    """Test 6: Regular Chat (No Screenshot)"""
    print("\n=== Test 6: Regular Chat ===")
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "message": "What are some tips for playing Minecraft?"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"AI Response: {result['response'][:200]}...")
        print("✓ Regular chat test completed")
    else:
        print(f"✗ Chat failed: {response.status_code}")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("PIXLY SCREENSHOT SYSTEM TEST SUITE")
    print("=" * 60)
    
    try:
        # Check if backend is running
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print("✓ Backend server is running\n")
    except requests.exceptions.ConnectionError:
        print("✗ Backend server is not running!")
        print("Please start the backend with: python run.py")
        return
    
    tests = [
        test_api_key_configuration,
        test_screenshot_capture,
        test_screenshot_retrieval,
        test_screenshot_deletion,
        test_chat_with_screenshot,
        test_chat_without_screenshot
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()