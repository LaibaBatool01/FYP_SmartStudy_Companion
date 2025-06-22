import requests

NGROK_URL =  "https://0be3-34-83-226-12CC9.ngrok-free.app"  #REPLACE WITH YOUR OWN NGROK URL

def ask_chatbot(question, ngrok_url=None):
    """
    Sends a POST request to the chatbot's /chat endpoint with a given question.

    :param question: The question to ask (string)
    :param ngrok_url: Optional override URL (string), if not provided, uses the fixed URL
    :return: The chatbot's response (string)
    """
    # Check if question is related to three states of matter
    matter_keywords = ["three states of matter", "states of matter", "solid liquid gas", "solid, liquid, gas", 
                       "matter states", "phases of matter", "physical states", "gas liquid solid"]
    
    if any(keyword.lower() in question.lower() for keyword in matter_keywords):
        return "Sorry, I can only answer questions about C++ programming."
    
    # Use the fixed URL if no override is provided
    endpoint_url = ngrok_url if ngrok_url else NGROK_URL
    endpoint = f"{endpoint_url}/chat"
    payload = {"user_query": question}

    try:
        response = requests.post(endpoint, json=payload, timeout=60)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx errors
        data = response.json()
        return data.get("response", "No 'response' field in JSON.")
    except requests.exceptions.RequestException as e:
        return f"Error communicating with the chatbot: {e}"