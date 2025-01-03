# Solcan Token Analyzer

This api uses Solscan to analyze specific tokens on the Solana blockchain. The agent takes a token's address as input and provide detailed insights about the top N wallets holding that token (where N is a variable I can configure).

The analysis includes the following for each wallet:

- How long the wallet has been active.
- Patterns of token holding (long-term holder vs. frequent flipper).
- How much of the specified token the wallet holds.
- How active the wallet is in transactions involving this token.
- Other tokens held by the wallet.

## Requirements

- Python 3.8+
- Solscan account pro subscription (for API access)

## Installation

1. **Fork and Clone the Repository**

   ```bash
   git clone <your-forked-repo-url>
   cd <repository-folder>
   ```

2. **Create a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   Create a `keys.env` file in the root directory with the following format:

   ```env
    # SOLSCAN API credentials
    SOLSCAN_API_KEY=<YOUR_SOLSCAN_API_KEY>

    # Top N wallets holding that token
    # Default: 10
    # N should be 10, 20, 30 or 40
    TOP_N=10
   ```

5. **Run the Bot**

   ```bash
   python index.py
   ```

## File Structure

- `index.py`: Main script that handles solscan API requests and data analysis.
- `keys.env`: Contains sensitive credentials and configurations.
- `requirements.txt`: Python dependencies for the project.

## Contributing

1. **Fork the Repository**: Click the fork button at the top of this page.
2. **Clone Your Fork**: Clone your forked repository to your local machine.

   ```bash
   git clone <your-forked-repo-url>
   ```

3. **Create a New Branch**: Create a feature branch for your changes.

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes and Commit**:

   ```bash
   git add .
   git commit -m "Add your message"
   ```

5. **Push to Your Fork**:

   ```bash
   git push origin feature/your-feature-name
   ```

6. **Submit a Pull Request**: Open a pull request to merge your changes into the main repository.
