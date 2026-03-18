import urllib.request, json
import sys

def test_summary():
    try:
        req = urllib.request.Request('http://localhost:8081/api/v1/patients/PT-1001')
        req.add_header('X-CDSS-Role', 'doctor')
        print("Testing AI Summary...")
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read())
        print("\nAI Summary Result:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error testing summary:", e)

def test_chatbot():
    try:
        req = urllib.request.Request('http://localhost:8081/api/v1/agent', data=b'{"message": "Hello"}', method='POST')
        req.add_header('X-CDSS-Role', 'doctor')
        req.add_header('Content-Type', 'application/json')
        print("\nTesting AI Chat bot...")
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read())
        print("\nChatbot Reply Result:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error testing chatbot:", e)

if __name__ == '__main__':
    test_summary()
    test_chatbot()
