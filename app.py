from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import os
import json
import sqlite3

import requests
from datetime import datetime
import schedule
import pytz
import random
import platform
import uuid
from discord_webhook import DiscordWebhook, DiscordEmbed
from pathlib import Path
from image_collage import combine_images, resize_gif
from typing import List
import IPython


# # from dotenv import load_dotenv, find_dotenv
# # # Load the .env file
# # load_dotenv(find_dotenv())

# # Access the variables as environment variables
# # WEIBO_AJAX_URL = "https://weibo.com/ajax/statuses/mymblog?uid=6593199887&page=1&feature=0"#
# WEIBO_AJAX_URL = os.getenv('WEIBO_AJAX_URL')
# WEIBO_URL = os.getenv('WEIBO_URL')
# MESSAGE_WEBHOOK_URL = os.getenv('MESSAGE_WEBHOOK_URL')
# STATUS_WEBHOOK_URL = os.getenv('STATUS_WEBHOOK_URL')

import toml

# Load TOML data from a file
CONFIG = toml.load('config.toml')


class WeiboScrapper:
    def __init__(self,account_names: List[str]):
        # Setup driver
        # add headless
        self.driver = self.new_driver()
        # create a sqlite database to store id
        # change to mongodb later
        self.db = sqlite3.connect('weibo.db')
        # let's hope weibo id is unique across all accounts
        self.cursor = self.db.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS weibo (id INTEGER PRIMARY KEY)''')
        self.db.commit()
        with open('kawaii_content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.kawaii_emojis = data['kawaii_emojis']
        self.kawaii_texts = data['kawaii_texts']
        self.kawaii_titles = data['kawaii_titles']
        self.should_delete_images = True
        # create a folder called images in the local directory if it does not exist
        if IPython.get_ipython() is None:
            # Not in Jupyter, use __file__
            self.image_dir = Path(__file__).parent / 'images'
        else:
            # In Jupyter, use the current working directory
            self.image_dir = Path(IPython.get_ipython().magic('pwd')) / 'images'
        self.image_dir.mkdir(exist_ok=True)
        self.account_names = account_names


    
    def new_driver(self):
        # Setup driver
        # add headless
        service = Service()
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(\
            service=service,options=options)
        return driver


    def start(self):
        # Run the scan immediately and then every 10 minutes
        for account in self.account_names:
            self.scan(CONFIG['weibo'][account])
        schedule.every(10).minutes.do(lambda: [self.scan(CONFIG['weibo'][account]) for account in self.account_names])
        # Run send_status immediately and then every hour
        self.send_status(CONFIG['status']['message_webhook'])
        schedule.every(6).hours.do(self.send_status,CONFIG['status']['message_webhook'])

        while True:
            schedule.run_pending()
            time.sleep(1)
        
    def get_weibo_content_once(self,endpoints):
        # check if the driver is alive
        if self.driver.service.is_connectable():
            pass
        else:
            self.driver.quit()
            self.driver = self.new_driver()

        try:
            self.driver.get(endpoints['ajax_url'])
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
    
    def check_id(self,item,endpoints):
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

    def add_all_id_to_db(self,endpoints):
        # add all id to the database
        # this is to prevent the program from sending old weibo
        content = self.get_weibo_content_loop(endpoints)
        if content:
            for item in content:
                self.cursor.execute('''INSERT INTO weibo (id) VALUES (?)''',(item['id'],))
                self.db.commit()
        else:
            print('failed to get content')
            return None       
        
    def create_webhook_instance(self,endpoints,**kwargs):
        if 'avatar_url' in endpoints:
            avatar_url = endpoints['avatar_url']
        else:
            avatar_url = None
        return DiscordWebhook(url=endpoints['message_webhook'],avatar_url=avatar_url,**kwargs)

    def get_weibo_content_loop(self,endpoints):
        i=0
        print(f'getting weibo content... @ {datetime.now()}')
        while True:
            content = self.get_weibo_content_once(endpoints)
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

    def scan(self,endpoints):
        content = self.get_weibo_content_loop(endpoints)
        if content:
            # in reverse order
            for item in reversed(content):
                if self.check_id(item,endpoints):
                    self.parse_item(item,endpoints)
                    time.sleep(5)
        else:
            print('failed to get content')
            return None
    
    def image_download(self, url: str):
        response = requests.get(url)
        if response.status_code == 200:
            # Use uuid to generate a random file name with the same extension
            file_name = str(uuid.uuid4()) + Path(url).suffix
            file_path = Path('images') / file_name
            file_path.write_bytes(response.content)
            return file_path
        else:
            print("Unable to download image. HTTP response code:", response.status_code)
            return None

    def images_download(self, URLs: list):
        # Download all images in the list to the local folder ./images
        # Return a list of local file paths
        return [self.image_download(url) for url in URLs]

    def images_delete(self, file_paths: list):
        # Delete all images in the list
        # Notice that file_paths could be status code
        for file_path in file_paths:
            if isinstance(file_path, (str, Path)):
                try:
                    Path(file_path).unlink()
                    # print(f"File {file_path} deleted.")
                except FileNotFoundError:
                    pass
                    # print(f"File {file_path} not found.")
            else:
                print(f"Invalid file path: {file_path}")


    def parse_item(self,item,endpoints):
        self.webhook_message = self.create_webhook_instance(endpoints)
        text_raw = item['text_raw']
        created_at = item['created_at']
        # title="塔菲の新微博喵~"
        title = endpoints['title']
        source= item['source']
        # use discord embed to display the content
        embed_color = 16738740
        dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
        discord_timestamp = dt.timestamp()
        # create the webhook
        # create the embed object
        embed = DiscordEmbed(title=title, description=text_raw, color=embed_color, url=endpoints['read_link_url'])
        embed.set_footer(text=f"来自 {source}")
        embed.set_timestamp(discord_timestamp)
        if 'retweeted_status' in item.keys():
            return self.parse_item_retweet(item,embed,endpoints)
        else:
            if 'pic_infos' in item.keys():
                return self.parse_item_with_images(item,embed,endpoints)
            elif 'page_info' in item.keys():
                if 'media_info' in item['page_info'].keys():
                    return self.parse_item_with_video(item,embed,endpoints)
                else:
                    if 'page_pic' in item['page_info'].keys():
                        return self.parse_item_with_page_pic(item,embed,endpoints)
                    else:
                        from uuid import uuid4
                        # write the whold item to a json file
                        with open(f'{str(uuid4())[-10:]}.json', 'w') as f:
                            json.dump(item, f)
                        raise Exception('Unknown page_info')
            else:
                return self.parse_item_text_only(item,embed,endpoints)
    
    def parse_item_with_page_pic(self, item, embed,endpoints):
        image_url = item['page_info']['page_pic']
        image_fp = self.image_download(image_url)
        with image_fp.open('rb') as f:
            self.webhook_message.add_file(file=f.read(), filename=image_fp.name)
        embed.set_image(url=f'attachment://{image_fp.name}')
        self.webhook_message.add_embed(embed)
        response = self.webhook_message.execute()
        if self.should_delete_images:
            self.images_delete([image_fp])
        return response.status_code

    def parse_item_text_only(self, item, embed, endpoints):
        # add the embed object to the webhook
        self.webhook_message.add_embed(embed)
        # execute the webhook
        response = self.webhook_message.execute()
        # check the response
        return response.status_code
    
    
    def parse_item_with_images(self, item, embed, endpoints):
        image_urls = [v['original']['url'] for k,v in item['pic_infos'].items()]
        image_filepaths = self.images_download(image_urls)
        # use discord embed to display the content
        # image_filenames = [os.path.basename(image_filepath) for image_filepath in image_filepaths]
        if len(image_filepaths) == 1:
            collage_image_path = image_filepaths[0]
        else:
            collage_image_path = combine_images(image_filepaths)
        with collage_image_path.open("rb") as f:
            self.webhook_message.add_file(file=f.read(), filename=collage_image_path.name)
        embed.set_image(url=f'attachment://{collage_image_path.name}')
        self.webhook_message.add_embed(embed)
        response = self.webhook_message.execute()
        if len(image_filepaths) > 1:
            time.sleep(1)
            self.send_animated_images(image_filepaths,endpoints)
        if self.should_delete_images:
            self.images_delete(image_filepaths)
            self.images_delete([collage_image_path])
        return response.status_code

    def send_animated_images(self, gif_candidates_paths, endpoints):
        # send a gif using self.webhook_message
        # return the status code of the request
        gif_webhook = self.create_webhook_instance(endpoints)
        files_to_delete = []
        for gif in gif_candidates_paths:
            if gif.suffix == ".gif":
                while gif.stat().st_size / (1024 ** 2) > 8:
                    # If the gif is larger than 8MB, resize it
                    gif = resize_gif(gif)
                    files_to_delete.append(gif)
                with gif.open("rb") as f:
                    gif_webhook.add_file(file=f.read(), filename=gif.name)
        # execute only if there is a gif
        if gif_webhook.files:
            response = gif_webhook.execute()
            if self.should_delete_images:
                self.images_delete(files_to_delete)
            return response.status_code
        else:
            return 204 # stands for no content
         


    def parse_item_with_video(self,item, embed,endpoints):
        video_url=item['page_info']['media_info']['stream_url']
        video_webhook = self.create_webhook_instance(endpoints=endpoints,content=video_url)
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
    
    def parse_item_retweet(self,item, embed, endpoints):
        retweet_text = item['retweeted_status']['text_raw']
        user_name=item['retweeted_status']['user']['screen_name']
        if 'pic_infos' in item['retweeted_status'].keys():
            image_urls=[v['original']['url'] for k,v in item['retweeted_status']['pic_infos'].items()]
            image_filepaths = self.images_download(image_urls)
            if len(image_filepaths) == 1:
                collage_image_path = image_filepaths[0]
            else:
                collage_image_path = combine_images(image_filepaths)
        if 'collage_image_path' in locals():
            # add the image to embed field
            with collage_image_path.open("rb") as f:
                self.webhook_message.add_file(file=f.read(), filename=collage_image_path.name)
            embed.set_image(url=f'attachment://{collage_image_path.name}')
        embed.add_embed_field(name=f"@{user_name}", value=retweet_text)
        self.webhook_message.add_embed(embed)
        response = self.webhook_message.execute()
        if self.should_delete_images and 'image_filepaths' in locals():
            self.images_delete(image_filepaths)
            self.images_delete([collage_image_path])
        return response.status_code
        

    def send_status(self,status_webhook_url):
        # send status to discord, say that the script is running, add some random kawaii emoji and text
        # use discord embed to display the content
        self.webhook_status = DiscordWebhook(url=status_webhook_url)
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
                                  color=embed_color)
        embed.set_timestamp()
        self.webhook_status.add_embed(embed)
        # execute the webhook
        response = self.webhook_status.execute()
        # check the response
        return response.status_code
    
if __name__ == "__main__":
    accounts=['ace_taffy','genshin_impact']
    # accounts=['ace_taffy']
    weibo_scrapper = WeiboScrapper(accounts)
    weibo_scrapper.start()