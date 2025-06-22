import requests

# Fixed default ngrok URL (similar to how it's defined in chatbot_api.py)
NGROK_URL = "https://7d4d-34-83-240-110.ngrok-free.app"

def get_quiz_on_topic(topic, ngrok_url=None):
    """
    Generate a quiz on a specific topic using the backend API
    """
    # Modify the topic to specify C++
    cpp_specific_topic = f"{topic} in C++"
    
    # Use the modified topic in the API call
    endpoint_url = ngrok_url if ngrok_url else NGROK_URL
    endpoint = f"{endpoint_url}/quiz"  # Changed from /generate_quiz to /quiz
    
    # Changed from POST with JSON payload to GET with query parameters
    try:
        response = requests.get(f"{endpoint}?topic={requests.utils.quote(cpp_specific_topic)}", timeout=60)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx errors
        data = response.json()
        return data.get("quiz", "No 'quiz' field in JSON response.")
    except requests.exceptions.RequestException as e:
        return f"Error communicating with the quiz generator: {e}"

def quiz_client():
    """
    Interactive client to use the quiz generator API.
    """
    # Replace this with your actual ngrok public URL
    ngrok_url = "https://7d4d-34-83-240-110.ngrok-free.app"
    
    if not ngrok_url:
        print("URL cannot be empty. Using a default value for testing.")
        ngrok_url = "https://7d4d-34-83-240-110.ngrok-free.app"
    
    print("\n=== Quiz Generator Client ===")
    print("This client connects to your quiz generator API via ngrok.")
    print("Type 'quit' at any time to exit.")
    
    while True:
        topic = input("\nEnter a topic for a 3-question quiz (Easy, Medium, Hard): ")
        

        if topic.lower() == 'quit':
            print("Exiting quiz generator client.")
            break
        
        print(f"\nGenerating quiz about '{topic}'... This may take a moment.")
        quiz = get_quiz_on_topic(topic, ngrok_url)
        
        print("\n=== Generated Quiz ===")
        print(quiz)
        print("=" * 50)

if __name__ == "__main__":
    quiz_client()