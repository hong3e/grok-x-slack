import os
import sys
import io
import logging
import requests
import smtplib
import re
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv

# Force sys.stdout to use UTF-8 to prevent UnicodeEncodeError in Windows environment
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from environment variables."""
    # Load .env file if it exists
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        logger.warning(".env file not found. Falling back to environment variables.")

    xai_api_key = os.getenv("XAI_API_KEY")
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    model = os.getenv("XAI_MODEL", "grok-2-latest")
    search_prompt = os.getenv(
        "SEARCH_PROMPT",
        "Find the most popular posts about stock investing, KOSPI, KOSDAQ, NASDAQ, NVIDIA, Tesla, and finance from the last 24 hours on X. Focus on posts with high likes, views, or retweets."
    )

    if not xai_api_key:
        logger.error("XAI_API_KEY is not set. Please check your .env file.")
        sys.exit(1)
        
    # Slack webhook check removed

    return {
        "api_key": xai_api_key,
        "webhook_url": slack_webhook_url,
        "model": model,
        "search_prompt": search_prompt,
        "gmail_user": os.getenv("GMAIL_USER"),
        "gmail_pass": os.getenv("GMAIL_APP_PASSWORD"),
        "receiver_email": os.getenv("RECEIVER_EMAIL")
    }

def fetch_grok_report(config):
    """Call xAI Responses API to fetch summarized X posts."""
    url = "https://api.x.ai/v1/responses"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }

    # Constructing the user prompt. We instruct the model to use the search tool,
    # find high-engagement posts, and output them in a formatted way.
    prompt_content = (
        f"{config['search_prompt']}\n\n"
        "Requirements for the output format:\n"
        "1. Search for both global stock posts (English) and domestic stock posts (Korean) on X.\n"
        "2. Extract 5 to 10 key posts from X (Twitter) within the last 24 hours. Blend them appropriately (e.g. 50% English posts, 50% Korean posts).\n"
        "3. For each post, you MUST write everything in Korean. If the original post is in English, translate the summary and metrics into natural Korean. Include:\n"
        "   - Combine Author name, handle, and post link on a SINGLE line like this: `*Author Name* (@username) / <POST_URL|원본트윗>`. You MUST bold the author name using single asterisks (`*Author Name*`). You MUST use the exact Slack link syntax `<POST_URL|원본트윗>` without any spaces inside the brackets.\n"
        "   - Core summary of the post written in Korean. Start directly with a bullet point ('• ') and DO NOT include the prefix '핵심 요약:'. The summary MUST be detailed and comprehensive (about 3-4 sentences, roughly 3 times longer than a basic summary), explaining the post's context, reasoning, and implications fully. DO NOT use any bolding or formatting (asterisks) within the summary text itself.\n"
        "   - You MUST include engagement metrics below the summary. Format them in Korean using icons and comma-separated numbers EXACTLY like this: '📊 반응 지표: 👁️ 3,434회 | ❤️ 35개 | 🔄 1회'. This is absolutely required for every single post. You MUST use commas for numbers over 1,000.\n"
        "4. ANTI-HALLUCINATION & INTEGRITY RULES (CRITICAL):\n"
        "   - You MUST ONLY report real, authentic posts that actually exist on X with their real, unique URLs. NEVER generate dummy, placeholder, or duplicate URLs. Each item must have its own unique, original X status link.\n"
        "   - Ensure the <POST_URL> is the exact, direct link to the ORIGINAL post (the parent tweet), NOT a link to a reply, quote tweet, or general thread link. It must directly point to the specific original tweet.\n"
        "   - You MUST summarize the actual post text (the tweet itself). DO NOT summarize the user's profile description, bio, or general account introduction. If you cannot find actual recent posts for a specific handle, skip that account and search for other high-engagement stock posts.\n"
        "5. Format the entire response in clean Markdown (Slack-friendly 'mrkdwn' format) and write all texts in Korean.\n"
        "   - Use bold by using single asterisks (`*text*`). NEVER use double asterisks (`**text**`) for bolding as Slack's mrkdwn format only supports single asterisks (`*text*`) for bold text.\n"
        "   - Use bullet points (`•`), and section dividers if helpful.\n"
        "   - Use emoji to highlight important sections (e.g. 📈, 🚀, 💬, 👤).\n"
        "   - After all posts, create ONE English prompt for an AI image generator (like DALL-E/Midjourney) that represents the overall sentiment, key topics, and financial concepts from these posts in a visually appealing way. Keep it under 2 sentences. Format it exactly as: `🎨 이미지 생성 프롬프트 (Image Prompt): [Your prompt here]`\n"
        "   - Below the Image Prompt, generate exactly 10 relevant hashtags in Korean for blog posting based on the content of the posts. Format it exactly as: `🏷️ 추천 해시태그: #hashtag1 #hashtag2 ...`"
    )

    payload = {
        "model": config["model"],
        "input": [
            {
                "role": "system",
                "content": (
                    "You are a professional stock market intelligence agent. Your job is to search X "
                    "for high-performing posts regarding stock investing and financial trends, analyze "
                    "them, and output a concise report. You must use the 'x_search' tool to find real-time X data."
                )
            },
            {
                "role": "user",
                "content": prompt_content
            }
        ],
        "tools": [{"type": "x_search"}],
        "temperature": 0.2
    }

    logger.info(f"Requesting report from xAI Grok API using model: {config['model']}...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        
        # Force encoding to utf-8 to prevent character corruption
        response.encoding = 'utf-8'
        
        # Handle HTTP errors
        if response.status_code != 200:
            logger.error(f"xAI API Request failed with status code {response.status_code}: {response.text}")
            response.raise_for_status()

        data = response.json()
        
        # Parse output_text from Responses API structure
        # The text is inside output[n].content[m].text where output[n].role is 'assistant' and type is 'message'
        output_text = None
        for item in data.get("output", []):
            if item.get("role") == "assistant" and "content" in item:
                for content_item in item["content"]:
                    if content_item.get("type") == "output_text":
                        output_text = content_item.get("text")
                        break
            if output_text:
                break

        if not output_text:
            logger.error(f"Unexpected response structure (failed to parse output_text): {data}")
            raise ValueError("Response body does not contain output_text.")
            
        logger.info("Successfully fetched report from Grok API.")
        return output_text

    except Exception as e:
        logger.error(f"Error while fetching Grok report: {e}")
        raise

def send_to_slack(webhook_url, text):
    """Send text message to Slack via Incoming Webhook."""
    payload = {
        "text": text
    }
    
    logger.info("Sending report to Slack...")
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Slack Webhook failed with status code {response.status_code}: {response.text}")
            response.raise_for_status()
            
        logger.info("Successfully sent report to Slack!")
        return True
    except Exception as e:
        logger.error(f"Error sending message to Slack: {e}")
        raise

def send_to_email(config, subject, text, image_path=None):
    """Send text message (and optional image) to an email address via Gmail SMTP."""
    sender = config.get("gmail_user")
    password = config.get("gmail_pass")
    receiver = config.get("receiver_email")
    
    if not sender or not password or not receiver:
        logger.warning("이메일 설정(GMAIL_USER, GMAIL_APP_PASSWORD, RECEIVER_EMAIL)이 누락되어 이메일을 발송하지 않습니다.")
        return False
        
    logger.info(f"Sending email to {receiver} via Gmail SMTP...")
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = subject
    
    # 이메일용 HTML 파싱 (슬랙 문법을 HTML로 변환)
    # <URL|텍스트> -> <a href="URL">텍스트</a>
    html_text = re.sub(r'<([^|>]+)\|([^|>]+)>', r'<a href="\1" style="color: #0066cc; text-decoration: none;">\2</a>', text)
    # *볼드* -> <b>볼드</b>
    html_text = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', html_text)
    # 줄바꿈 -> <br>
    html_text = html_text.replace('\n', '<br>\n')
    
    msg.attach(MIMEText(html_text, 'html', 'utf-8'))
    
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            msg.attach(image)
            logger.info(f"Attached image: {image_path}")
        except Exception as e:
            logger.error(f"Failed to attach image: {e}")
            
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        logger.info("Successfully sent email!")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def main():
    logger.info("Starting Grok X Stock Market Notifier...")
    
    # 1. Load configuration
    config = load_config()
    
    try:
        # 2. Get report from Grok API (using search tool on X)
        report = fetch_grok_report(config)
        
        # 3. Format header
        email_message = (
            "🔔 *[Grok X Stock Intelligence Report]* 🔔\n"
            "Here are the top trending stock-related posts on X from the past 24 hours:\n\n"
            f"{report}"
        )
        
        # 4. Preview the message
        print("\n" + "="*60)
        print("📢 [이메일 전송 메시지 미리보기 / Email Message Preview]")
        print("="*60)
        print(email_message)
        print("="*60 + "\n")
        
        # 5. Interactive prompt to confirm sending
        # If --yes option is provided or NON_INTERACTIVE=true is set in env, skip confirmation.
        is_interactive = True
        if "--yes" in sys.argv or os.getenv("NON_INTERACTIVE") == "true":
            is_interactive = False
            
        if is_interactive:
            try:
                user_input = input("위 메시지를 이메일로 전송하시겠습니까? (y/n, 기본값: y): ").strip().lower()
                if user_input not in ("", "y", "yes"):
                    logger.info("전송이 사용자에 의해 취소되었습니다. (Cancelled by user)")
                    return
            except KeyboardInterrupt:
                logger.info("\n전송이 취소되었습니다. (Cancelled)")
                return
        
        # 5. Send to Email
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        email_subject = f"지난 24시간 X(트위터) 주식·금융 인기 포스트 분석 보고서 ({today_str})"
        send_to_email(config, email_subject, email_message)
        
        logger.info("Notification process completed successfully.")
        
    except Exception as e:
        logger.error(f"Process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
