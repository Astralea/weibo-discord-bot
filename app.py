from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import os
import json
import sqlite3
from dotenv import load_dotenv
import requests
from datetime import datetime
import schedule
import pytz
import random
import platform
import uuid
from discord_webhook import DiscordWebhook, DiscordEmbed


# Load the .env file
load_dotenv()

# Access the variables as environment variables
WEIBO_AJAX_URL = os.getenv('WEIBO_AJAX_URL')
WEIBO_URL = os.getenv('WEIBO_URL')
MESSAGE_WEBHOOK_URL = os.getenv('MESSAGE_WEBHOOK_URL')
STATUS_WEBHOOK_URL = os.getenv('STATUS_WEBHOOK_URL')


class WeiboScrapper:
    def __init__(self):
        # Setup driver
        # add headless
        self.driver = self.new_driver()
        # create a sqlite database to store id
        # change to mongodb later
        self.db = sqlite3.connect('weibo.db')
        self.cursor = self.db.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS weibo (id INTEGER PRIMARY KEY)''')
        self.db.commit()
        with open('kawaii_content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.kawaii_emojis = data['kawaii_emojis']
        self.kawaii_texts = data['kawaii_texts']
        self.kawaii_titles = data['kawaii_titles']
        # create a folder called images in the local directory if it does not exist
        self.image_dir='images'
        if not os.path.exists(self.image_dir):
            os.mkdir(self.image_dir)


    
    def new_driver(self):
        # Setup driver
        # add headless
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(\
            service=Service(ChromeDriverManager().install())\
                ,options=options)
        return driver


    def start(self):
        # Run the scan immediately and then every 10 minutes
        self.scan()
        schedule.every(10).minutes.do(self.scan)

        # Run send_status immediately and then every hour
        self.send_status()
        schedule.every(3).hours.do(self.send_status)

        while True:
            schedule.run_pending()
            time.sleep(1)
        
    def get_weibo_content_once(self):
        # check if the driver is alive
        if self.driver.service.is_connectable():
            pass
        else:
            self.driver.quit()
            self.driver = self.new_driver()

        try:
            self.driver.get(WEIBO_AJAX_URL)
            # Wait for the dynamic content to load
            time.sleep(10)
            self.driver.implicitly_wait(20)
            pre_tag = self.driver.find_element(By.TAG_NAME, 'pre')
            json_text = pre_tag.text
        except Exception as e:
            print(e)
            return None
        content = json.loads(json_text) # content is a dictionary
        return content['data']['list']
    
    def check_id(self,item):
        # if id is not in the database, return True
        # else return False
        weibo_item_id=item['id']
        self.cursor.execute('''SELECT * FROM weibo WHERE id=?''',(weibo_item_id,))
        if self.cursor.fetchone() is None:
            #write the id to the database
            self.cursor.execute('''INSERT INTO weibo (id) VALUES (?)''',(weibo_item_id,))
            self.db.commit()
            return True
        else:
            return False       

    def get_weibo_content_loop(self):
        i=0
        print(f'getting weibo content... @ {datetime.now()}')
        while True:
            content = self.get_weibo_content_once()
            if content:
                break   
            print('retrying...')
            time.sleep(60)
            i+=1
            print(i)
            if i>10:
                print('failed')
                return None
        return content

    def scan(self):
        content = self.get_weibo_content_loop()
        if content:
            for item in content:
                if self.check_id(item):
                    self.parse_item(item)
                    time.sleep(5)
        else:
            print('failed to get content')
            return None
        

    def image_download(self,url:str):
        response = requests.get(url) #stream value doesn't matter
        if response.status_code == 200:
            # use uuid to generate a random file name with the same extension
            file_name = str(uuid.uuid4()) + os.path.splitext(url)[1]
            file_path = os.path.join('images',file_name)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        else:
            print("Unable to download image. HTTP response code:", response.status_code)

    def images_download(self,URLs:list):
        # download all images in the list to the local folder ./images
        # return a list of local file paths
        file_paths = []
        for url in URLs:
            file_path = self.image_download(url)
            file_paths.append(file_path)
        return file_paths

    def images_delete(self,file_paths:list):
        # delete all images in the list
        # notice that file_paths could be status code
        for file_path in file_paths:
            if type(file_path) == str:
                os.remove(file_path)

    def parse_item(self,item):
        self.webhook_message = DiscordWebhook(url=MESSAGE_WEBHOOK_URL)
        text_raw = item['text_raw']
        created_at = item['created_at']
        title="塔菲の新微博喵~"
        source= item['source']
        # use discord embed to display the content
        embed_color = 16738740
        dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
        discord_timestamp = dt.timestamp()
        # create the webhook
        # create the embed object
        embed = DiscordEmbed(title=title, description=text_raw, color=embed_color, url=WEIBO_URL)
        embed.set_footer(text=f"来自 {source}")
        embed.set_timestamp(discord_timestamp)
        if 'pic_infos' in item.keys():
            return self.parse_item_with_images(item,embed)
        elif 'page_info' in item.keys():
            return self.parse_item_with_video(item,embed)
        elif 'retweeted_status' in item.keys():
            return self.parse_item_retweet(item,embed)
        else:
            return self.parse_item_text_only(item,embed)

    def parse_item_text_only(self, item, embed):
        # add the embed object to the webhook
        self.webhook_message.add_embed(embed)
        # execute the webhook
        response = self.webhook_message.execute()
        # check the response
        return response.status_code
    
    def parse_item_with_images(self,item, embed):
        #TODO: collage the images
        image_urls = [v['original']['url'] for k,v in item['pic_infos'].items()]
        image_filepaths = self.images_download(image_urls)
        # use discord embed to display the content
        image_filenames = [os.path.basename(image_filepath) for image_filepath in image_filepaths]
        
        image_name = image_filenames[0]
        with open(os.path.join(self.image_dir,image_name ), "rb") as f:
            self.webhook_message.add_file(file=f.read(), filename=image_name )
        embed.set_image(url=f'attachment://{image_name}')


        self.webhook_message.add_embed(embed)
        response = self.webhook_message.execute()
        self.images_delete(image_filepaths)
        return response.status_code

    def parse_item_with_video(self,item, embed):
        video_url=item['page_info']['media_info']['stream_url']

        video_webhook = DiscordWebhook(url=MESSAGE_WEBHOOK_URL,content=video_url)
        self.webhook_message.add_embed(embed)
        response1 = self.webhook_message.execute()
        response2 = video_webhook.execute()
        # return 200 if both requests are successful(200,204, etc., start with 2)
        # otherwise return the status code of the first failed request
        if response1.status_code < 300 and response2.status_code < 300:
            return 200
        elif response1.status_code < 300 and response2.status_code >= 300:
            return response2.status_code
        else:
            return response1.status_code
    
    def parse_item_retweet(self,item, embed):
        #TODO: add images
        # content[7]['retweeted_status']['pic_infos']
        retweet_text = item['retweeted_status']['text_raw']
        user_name=item['retweeted_status']['user']['screen_name']
        embed.add_embed_field(name=user_name, value=retweet_text)
        self.webhook_message.add_embed(embed)
        response = self.webhook_message.execute()
        return response.status_code
        

    def send_status(self):
        # send status to discord, say that the script is running, add some random kawaii emoji and text
        # use discord embed to display the content
        self.webhook_status = DiscordWebhook(url=STATUS_WEBHOOK_URL)
        embed_color = 16738740
        emoji = random.choice(self.kawaii_emojis)
        text = random.choice(self.kawaii_texts)
        title = random.choice(self.kawaii_titles)
        if platform.system() == 'Windows':
            machine_info = f"{platform.node()} {platform.machine()}"
        else:
            machine_info = f"{os.uname().nodename} {os.uname().machine}"
        # TODO: use chatgpt to generate random text
        # get current time, up to seconds, timezone GMT+9
        timezone = pytz.timezone('Etc/GMT-9')
        # Get current time up to seconds in GMT+9
        time_now = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        embed = DiscordEmbed(title=title, \
                             description=f"{emoji} {text} @ {time_now} -- {machine_info}",\
                                  color=embed_color, \
                                    url=STATUS_WEBHOOK_URL)
        embed.set_timestamp()
        self.webhook_status.add_embed(embed)
        # execute the webhook
        response = self.webhook_status.execute()
        # check the response
        return response.status_code
    
if __name__ == "__main__":
    weibo_scrapper = WeiboScrapper()
    weibo_scrapper.start()