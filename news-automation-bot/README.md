# Python News Aggregator & Telegram Bot

A Python-based automated news aggregation system that collects Ukrainian news from multiple RSS sources, analyzes articles by topic relevance, stores processed news in SQLite, and publishes new articles to a Telegram channel.

## Overview

This project demonstrates how Python can be used to build an automated content-processing and publishing workflow.

The application:

* Collects news from multiple Ukrainian RSS feeds
* Processes and cleans article text
* Classifies news by relevance
* Extracts article images when available
* Prevents duplicate publications
* Stores processed articles in SQLite
* Publishes news automatically to Telegram
* Handles Telegram API errors and rate limits
* Runs continuously with scheduled checks

## Features

### RSS News Collection

The application currently collects news from:

* Ukrainska Pravda
* RBC-Ukraine
* NV

New sources can be added through the `SOURCES` configuration.

### News Classification

Articles are analyzed using keyword-based classification.

Keywords are divided into three groups:

* Strong keywords — 3 points
* Medium keywords — 2 points
* Weak keywords — 1 point

Articles with a score of 3 or more are marked as:

`🔴 IMPORTANT`

Other articles are marked as:

`🟡 REGULAR`

The classification system can be expanded with additional keywords and rules.

### Duplicate Prevention

Processed articles are stored in an SQLite database.

Each article is identified by its unique URL.

This prevents the same article from being published multiple times.

### Image Extraction

The application attempts to extract article images from:

* RSS media content
* RSS thumbnails
* Enclosures
* Images included in article descriptions

If an image is available, it is sent to Telegram together with the article.

### Telegram Integration

The bot publishes articles directly to a Telegram channel using the Telegram Bot API.

The application supports:

* Text messages
* Image posts
* HTML formatting
* Telegram API error handling
* Rate-limit handling

### Continuous Automation

The application checks RSS feeds every 5 minutes.

This allows the bot to operate continuously without manual intervention.

## Application Flow

```text
RSS Sources
     ↓
Fetch News
     ↓
Clean Article Data
     ↓
Classify News
     ↓
Extract Image
     ↓
Check SQLite Database
     ↓
Publish to Telegram
     ↓
Save Article
     ↓
Wait 5 Minutes
     ↓
Repeat
```

## Technologies

* Python
* RSS / XML
* Feedparser
* Requests
* SQLite
* Telegram Bot API
* Regular Expressions
* HTML processing

## Project Structure

```text
python-news-telegram-bot/
│
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── news.db
```

`news.db` is created automatically when the application starts and should not be committed to GitHub.

## Requirements

* Python 3.10+
* Telegram bot
* Telegram channel where the bot has permission to publish messages

## Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd python-news-telegram-bot
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file locally:

```env
BOT_TOKEN=your_telegram_bot_token_here
```

Never commit the real Telegram bot token to GitHub.

The `.env` file is excluded through `.gitignore`.

## Telegram Configuration

1. Create a Telegram bot using BotFather.
2. Copy the bot token.
3. Add the bot to your Telegram channel.
4. Give the bot permission to publish messages.
5. Set the `BOT_TOKEN` environment variable.

The current channel is configured in `main.py`.

## Running the Application

Run:

```bash
python main.py
```

The application will:

1. Create the SQLite database.
2. Store existing RSS articles during the first run.
3. Avoid publishing old articles.
4. Start checking for new articles.
5. Publish new articles to Telegram.
6. Repeat the process every 5 minutes.

## Database

SQLite is used to store information about published articles.

The database contains:

* Article ID
* Article URL
* Article title

The database allows the application to detect previously processed articles.

## Error Handling

The application includes handling for:

* RSS source errors
* Network errors
* Telegram API errors
* Telegram rate limits
* Missing article images
* Empty RSS feeds

Telegram rate limits are handled using the `retry_after` value returned by the API.

## Security

Sensitive configuration is stored outside the source code using environment variables.

The following files are excluded from Git:

```text
.env
*.db
*.sqlite
*.sqlite3
```

The repository should never contain a real Telegram bot token.

## Future Improvements

Possible future improvements include:

* More Ukrainian and international news sources
* Better news relevance scoring
* AI-based article classification
* Automatic article summarization
* Automatic translation
* Scheduled publishing
* Telegram post formatting improvements
* Persistent logging
* Configuration through environment variables
* Unit and integration tests
* Docker support
* Deployment to a cloud server

## Portfolio Purpose

This project was created as a practical Python automation project demonstrating:

* API integration
* RSS data collection
* Data processing
* SQLite database management
* Automation
* Error handling
* Telegram Bot API integration
* Basic text classification
* Working with external services

The project can be extended into a production-ready automated news monitoring and publishing system.
