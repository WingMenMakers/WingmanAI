# api_test.py
import requests
import json

# REPLACE THIS WITH your current ngrok URL
API_BASE_URL = "https://semiconvergence-danna-inadequate.ngrok-free.dev"
API_URL = f"{API_BASE_URL}/query"  # <--- CRITICAL FIX: Append /query

TEST_QUERIES = [
    # # 1. Simple Web Search (Should succeed fully)
    # {"query": "What is the capital of Australia?"}, 
    
    # 2. Ambiguous Email (Should fail gracefully with INCOMPLETE status)
    {"query": "Check my inbox for new mails."},
    
    # # 3. Weather (Should succeed, but use default current location)
    # {"query": "Will it rain today?"},

    {"query": "Read me the mail from Indian Oil Corporation Limited."}
]

def run_tests():
    print(f"--- Testing Wingman API at {API_URL} ---")
    
    for i, data in enumerate(TEST_QUERIES):
        print(f"\nQUERY {i+1}: {data['query']}")
        
        try:
            response = requests.post(
                API_URL,
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
            
            result = response.json()
            
            # 🎯 NEW: Print the entire formatted JSON response for complete visibility
            print("\n--- FULL API RESPONSE ---")
            print(json.dumps(result, indent=4))
            print("-------------------------")
            
        except requests.exceptions.RequestException as e:
            # Handle HTTP errors cleanly
            if e.response is not None:
                print(f"!!! HTTP ERROR: {e.response.status_code} {e.response.reason}")
                try:
                    print(f"!!! SERVER DETAIL: {e.response.json()}")
                except:
                    print(f"!!! SERVER DETAIL: {e.response.text[:100]}...")
            else:
                 print(f"!!! REQUEST ERROR: {e}")
        except json.JSONDecodeError:
            print(f"!!! JSON ERROR: Could not decode response.")
        except Exception as e:
            print(f"!!! UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    run_tests()