import requests
import http.cookiejar

class CookieManager:
    def __init__(self, cookie_file="amazon_cookies.txt"):
        self.cookie_file = cookie_file
        # Use MozillaCookieJar for better compatibility with standard cookie files
        self.cookie_jar = http.cookiejar.MozillaCookieJar(self.cookie_file)
        self.load_cookies()  # Try to load existing cookies

    def load_cookies(self):
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
            print("Loaded cookies from cache.")
        except FileNotFoundError:
            print("Cookie file not found, will create one.")
        except Exception as e:
            print(f"Error loading cookies: {e}")

    def save_cookies(self):
        try:
            self.cookie_jar.save(ignore_discard=True, ignore_expires=True)
            print("Cookies saved to cache.")
        except Exception as e:
            print(f"Error saving cookies: {e}")

    def get_session(self):
        session = requests.Session()
        session.cookies = self.cookie_jar
        # Update headers to closely mimic a real browser request
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
            # Additional headers (such as sec-ch-ua) can be added if needed
        })
        return session

# Example Usage:
if __name__ == '__main__':
    cookie_manager = CookieManager()
    session = cookie_manager.get_session()
    response = session.get("https://www.amazon.com")
    if response.status_code == 200:
        print("Successfully fetched Amazon homepage.")
        cookie_manager.save_cookies()  # Save initial cookies
    else:
        print(f"Failed to fetch Amazon homepage: {response.status_code}")
