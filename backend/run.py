from app import app

if __name__ == "__main__":
    # Bind to 0.0.0.0 and port 3001 for container preview compatibility
    app.run(host="0.0.0.0", port=3001)
