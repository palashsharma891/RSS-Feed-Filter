# -*- coding: utf-8 -*-
"""
Created on Sat Jun  6 13:03:47 2020

@author: Palash
"""

import feedparser
import string
import time
import threading
from project_util import translate_html
from mtTkinter import *
from datetime import datetime
import pytz
import sys
sys.setrecursionlimit(5000)

#-----------------------------------------------------------------------

#======================
# Code for retrieving and parsing
# Google news feed
#======================

def process(url):
    """
    Fetches news items from the rss url and parses them.
    Returns a list of NewsStory-s.
    """
    feed = feedparser.parse(url)
    entries = feed.entries
    ret = []
    for entry in entries:
        guid = entry.guid
        title = translate_html(entry.title)
        link = entry.link
        description = translate_html(entry.description)
        pubdate = translate_html(entry.published)

        try:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
            pubdate.replace(tzinfo=pytz.timezone("GMT"))
            # pubdate = pubdate.astimezone(pytz.timezone('EST'))
            # pubdate.replace(tzinfo=None)
        except ValueError:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %z")

        newsStory = NewsStory(guid, title, description, link, pubdate)
        ret.append(newsStory)
    return ret


class NewsStory(object):
    """
    Represents a NewsStory data type containing attributes such as:
    title, description, link and pubdate
    """
    
    def __init__(self, guid, title, description, link, pubdate):
        """
        Constructor to initialize the NewsStory object
        """
        self.guid = guid
        self.title = title
        self.description = description
        self.link = link
        self.pubdate = pubdate

    def get_guid(self):
        """Getter for guid: Globally Unique Identifier"""
        return self.guid

    def get_title(self):
        """Getter for title of the story"""
        return self.title

    def get_description(self):
        """Getter for description of the story"""
        return self.description

    def get_link(self):
        """Getter for link to more content"""
        return self.link

    def get_pubdate(self):
        """Getter for publication date"""
        return self.pubdate


class Trigger(object):
    """
    Represents a trigger class
    """
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        # since the trigger class is never called directly
        raise NotImplementedError 


class PhraseTrigger(Trigger):
    """
    Represents a phrase trigger
    """
    def __init__(self, phrase):
        """
        Constructor to initialize the phrase
        """
        self.phrase = phrase
    
    def is_phrase_in(self, text):
        """
        Returns True if the phrase is in the news story, False otherwise
        """
        # Clean the text, phrase; adding in terminal space as delimiter
        no_punct_text = ''.join(ch if ch not in string.punctuation else ' ' for ch in text.upper())
        cleaned_text = ' '.join(no_punct_text.split()) + ' '
        no_punct_phrase = ''.join(ch if ch not in string.punctuation else ' '
                for ch in self.phrase.upper())
        cleaned_phrase = ' '.join(no_punct_phrase.split()) + ' '
        
        # Search cleaned text for instance of exact phrase
        if cleaned_phrase not in cleaned_text:
            return False
        else:
            return True


class TitleTrigger(PhraseTrigger):
    """
    Represents a title trigger
    """
    def evaluate(self, story):
        """
        Returns True if the story's title contains the phrase, False otherwise
        """
        return self.is_phrase_in(story.get_title())


class DescriptionTrigger(PhraseTrigger):
    """
    Represents a description trigger
    """
    def evaluate(self, story):
        """
        Returns True if the story's description contains the phrase,
        False otherwise
        """
        return self.is_phrase_in(story.get_description())


class TimeTrigger(Trigger):
    """
    Represents a time trigger
    """
    def __init__(self, str_time):
        """
        Constructor to initlaize the time with the proper datetime object in EST
        """
        # Convert string to 'datetime' object, set timezone to EST
        time = datetime.strptime(str_time, "%d %b %Y %H:%M:%S")
        # time = time.replace(tzinfo=pytz.timezone("EST"))

        self.time = time


class BeforeTrigger(TimeTrigger):
    """
    Represents a before-given-time trigger
    """
    def evaluate(self, story):
        """
        Returns True if the story was publihed before the given time, 
        False otherwise
        """
        try:
            condition = story.get_pubdate() < self.time
        except:
            self.time = self.time.replace(tzinfo=pytz.timezone("EST"))
            condition = story.get_pubdate() < self.time
        
        if condition: 
            return True
        else:
            return False


class AfterTrigger(TimeTrigger):
    """
    Represents an after-given-time trigger
    """
    def evaluate(self, story):
        """
        Returns True if the story was published after the given time, 
        False otherwise
        """
        try:
            condition = story.get_pubdate() > self.time
        except:
            self.time = self.time.replace(tzinfo=pytz.timezone("EST"))
            condition = story.get_pubdate() > self.time
        
        if condition: 
            return True
        else:
            return False


class NotTrigger(Trigger):
    """
    Represents a 'not' trigger
    """
    def __init__(self, T):
        """
        Constructor to initalize the trigger
        """
        self.T = T

    def evaluate(self, story):
        """
        Returns True if the given is not fired for the given story, 
        False otherwise
        """
        return not self.T.evaluate(story)


class AndTrigger(Trigger):
    """
    Represents an 'And' trigger
    """
    def __init__(self, T1, T2):
        """
        Constructor to initialize two triggers
        """
        self.T1 = T1
        self.T2 = T2

    def evaluate(self, story):
        """
        Returns the value of logical '&&' operation performed on the triggers
        """
        return self.T1.evaluate(story) and self.T2.evaluate(story)



class OrTrigger(Trigger):
    """
    Reprsents an 'Or' trigger
    """
    def __init__(self, T1, T2):
        """
        Constructor to initialize two triggers
        """
        self.T1 = T1
        self.T2 = T2

    def evaluate(self, story):
        """
        Returns the value of logical '||' operation performed on the triggers
        """
        return self.T1.evaluate(story) or self.T2.evaluate(story)


def filter_stories(stories, triggerlist):
    """
    Takes in a list of NewsStory instances.
    Returns: a list of only the stories for which a trigger in triggerlist fires.
    """
    filtered_stories = []
    for story in stories:
        if any([T.evaluate(story) for T in triggerlist]):
            filtered_stories.append(story) 
    
    return filtered_stories


SLEEPTIME = 60 #seconds -- how often we poll

def main_thread(master):
    
    try:
        t1 = TitleTrigger("Trump")
        t2 = DescriptionTrigger("Trump")
#        t3 = DescriptionTrigger("Twitter")
#        t4 = AndTrigger(t1, t3)
        triggerlist = [t1, t2]#, t4]

        # Draws the popup window that displays the filtered stories
        # Retrieves and filters the stories from the RSS feeds
        frame = Frame(master)
        frame.pack(side=BOTTOM)
        scrollbar = Scrollbar(master)
        scrollbar.pack(side=RIGHT,fill=Y)

        t = "Google Top News"
        title = StringVar()
        title.set(t)
        ttl = Label(master, textvariable=title, font=("Helvetica", 18))
        ttl.pack(side=TOP)
        cont = Text(master, font=("Helvetica",14), yscrollcommand=scrollbar.set)
        cont.pack(side=BOTTOM)
        cont.tag_config("title", justify='center')
        button = Button(frame, text="Exit", command=root.destroy)
        button.pack(side=BOTTOM)
        guidShown = []
        def get_cont(newstory):
            if newstory.get_guid() not in guidShown:
                cont.insert(END, newstory.get_title()+"\n", "title")
                cont.insert(END, "\n---------------------------------------------------------------\n", "title")
                cont.insert(END, newstory.get_description())
                cont.insert(END, "\n*********************************************************************\n", "title")
                guidShown.append(newstory.get_guid())

        while True:
            
            print("Polling . . .", end=' ')
            # Get stories from Google's Top Stories RSS news feed
            stories = process("http://news.google.com/news?output=rss")

            stories = filter_stories(stories, triggerlist)

            list(map(get_cont, stories))
            scrollbar.config(command=cont.yview)

            print("Sleeping...")
            time.sleep(SLEEPTIME)

    except Exception as e:
        print(e)


if __name__ == '__main__':
    root = Tk()
    root.title("Some RSS parser")
    t = threading.Thread(target=main_thread, args=(root,))
    t.start()
    root.mainloop()
