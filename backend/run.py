from app import create_app

app = create_app()

if __name__ == '__main__':
    port = 8002  # Changed port to avoid conflicts
    print(f"Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True) 