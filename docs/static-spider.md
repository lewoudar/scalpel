# Static spider

Pyscalpel aims to provide a simple interface to write spiders. To demonstrate it, we will try to scrape quotes on
[quotes.toscrape](https://quotes.toscrape.com/). I will assume you already installed Pyscalpel following the
[installation](installation.md) guide.

## Learning HTML, CSS and XPATH

This guide will not be a course on HTML or CSS / XPATH selectors. If you are not familiar with these technologies, there
are many resources on the web but I will give you a few that I know.

For HTML:

- [W3Schools](https://www.w3schools.com/html/)
- [Mozilla Developer Network](https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML/Getting_started)

For CSS:

- [W3Schools](https://www.w3schools.com/css/default.asp)
- [Mozilla Developer Network](https://developer.mozilla.org/en-US/docs/Learn/CSS/Building_blocks/Selectors)

For XPATH:

- [W3Schools](https://www.w3schools.com/xml/xpath_intro.asp)
- [XPATH cheatsheet](https://devhints.io/xpath)
- [Equivalent XPATH/CSS - Wikibooks](https://en.wikibooks.org/wiki/XPath/CSS_Equivalents)


## Our first spider

Ok, let's create a file *spider.py* with the following content:

```python
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print('hello spider')


static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
static_spider.run()
```

if you prefer `trio` over `gevent`, this is the equivalent:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print('hello spider')

async def main() -> None:
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
    await spider.run()

trio.run(main)
```

!!! note
    there is an icon at the top right of the code where you can click to copy and paste into your editor and test it.

If you run this program, you will just see `hello spider` printed in your console. Nothing exciting right now, let's
change that.

We can inspect the HTML source of the page to have a clear idea of what we can scrape. To do that on a browser, typically
the combination `ctrl + u` can be used. Let's say we want a to print the title of the page.

With gevent:

```python
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print(response.css('title').get())
    print(response.xpath('//title').get())


static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
static_spider.run()
```

with trio:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print(response.css('title').get())
    print(response.xpath('//title').get())

async def main() -> None:
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
    await spider.run()

trio.run(main)
```

If you run the program, the content `<title>Quotes to Scrape</title>` will be printed twice. I deliberately wrote the 
instruction to select the title twice to demonstrate how to use css and xpath selectors on the `StaticResponse` object.

!!! note
    The css and xpath methods are shortcuts to the parsel 
    [Selector](https://parsel.readthedocs.io/en/latest/parsel.html#module-parsel.selector) methods. Moreover these methods
    return a [SelectorList](https://parsel.readthedocs.io/en/latest/parsel.html#parsel.selector.SelectorList) where you
    can apply further filters. To know more about parsel, you can read the 
    [documentation](https://parsel.readthedocs.io/en/latest/parsel.html#parsel.selector.SelectorList) but we will cover
    some features in this guide.

So far we have the tag plus its content printed. What if we only want the content? Pretty easy, we just need to
add an additional information to our selectors.

With gevent:

```python
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print(response.css('title::text').get())
    print(response.xpath('//title/text()').get())


static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
static_spider.run()
```

With trio:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    print(response.css('title::text').get())
    print(response.xpath('//title/text()').get())

async def main() -> None:
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
    await spider.run()

trio.run(main)
```

Now we have `Quotes to Scrape` printed, yeah! You will notice the pseudo-selector `::text` for the css method and the
property `/text()` for the xpath method which help to obtain the desired text.

Now if we look carefully at the html source of the website, we notice that all quote information have this skeleton:

```html
<div class="quote" itemscope itemtype="http://schema.org/CreativeWork">
    <span class="text" itemprop="text">“The world as we have created it is a process of our thinking.
     It cannot be changed without changing our thinking.”</span>
    <span>by <small class="author" itemprop="author">Albert Einstein</small>
    <a href="/author/Albert-Einstein">(about)</a>
    </span>
    <div class="tags">
        Tags:
        <meta class="keywords" itemprop="keywords" content="change,deep-thoughts,thinking,world" /    > 
        <a class="tag" href="/tag/change/page/1/">change</a>
        <a class="tag" href="/tag/deep-thoughts/page/1/">deep-thoughts</a>
        <a class="tag" href="/tag/thinking/page/1/">thinking</a>
        <a class="tag" href="/tag/world/page/1/">world</a>
    </div>
</div>
```

Inside the `<div class="quote"..>` we have a `<span class="text"..>` holding the quote so if we want to print all quotes
of the page we can do as follow.

With gevent:

```python
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        print(quote.xpath('./span[@class="text"]/text()').get())

static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
static_spider.run()
```

With trio:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        print(quote.xpath('./span[@class="text"]/text()').get())

async def main() -> None:
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
    await spider.run()

trio.run(main)
```

We will see an output like the following (I truncated it here):

```bash
“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
“It is our choices, Harry, that show what we truly are, far more than our abilities.”
...
```

Victory! We have all the quotes printed!

If you are wondering *why the for loop?*, remember that `xpath` and `css` response methods return 
[SelectorList](https://parsel.readthedocs.io/en/latest/parsel.html#parsel.selector.SelectorList) objects so we can
iterate on it. Also if you look the second selector `./span[@class="text"]/text()`, you noticed that it starts with `./`
it is because the new search is relative the first one, we search inside the ``<div class="quote"..>`` quote elements.
If this seems unclear for you, don't hesitate to look at the
 [parsel tutorial](https://parsel.readthedocs.io/en/latest/usage.html) before continuing this guide.
 
Ok now let's scrape the author of the quote and the related tags. The author is inside a `<small class="author"..>`
and tags are inside `<a>` tags which are also inside a `<div class='tags'..>`. So with this knowledge, we can write the
following code.
 
With gevent:
 
```python
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        print('===', quote.xpath('./span/small/text()').get(), '===')
        print('quote:', quote.xpath('./span[@class="text"]/text()').get())
        print('tags', quote.xpath('./div/a/text()').getall())
        print()

static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
static_spider.run()
```

With trio:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        print('===', quote.xpath('./span/small/text()').get(), '===')
        print('quote:', quote.xpath('./span[@class="text"]/text()').get())
        print('tags', quote.xpath('./div/a/text()').getall())
        print()

async def main() -> None:
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse)
    await spider.run()

trio.run(main)
```

We have the following output (I truncated it here):

```bash
=== Albert Einstein ===
quote: “The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
tags ['change', 'deep-thoughts', 'thinking', 'world']

=== J.K. Rowling ===
quote: “It is our choices, Harry, that show what we truly are, far more than our abilities.”
tags ['abilities', 'choices']
...
```

There we goooo! May be you noticed usage of 
[Selector.getall](https://parsel.readthedocs.io/en/latest/parsel.html#parsel.selector.SelectorList.getall) for the tags.
This is because we have many elements matching the selector and we want all the values. This is different from the `get`
method which returns only the first element of the list.

Now that we have all these items, you probably want to store them somewhere and do further processing after. You can
choose whatever you want to store the data, a relational database, a NoSQL database, cloud services, etc.. pyscalpel
does not bother you to do want you want with your data, but for our example we will store the scraped items in a file
using some pyscalpel utilities.

First of all, pyscalpel comes with a handy [Configuration](api.md#configuration) object to store many settings related to
our spider. A particular interesting one is `backup_filename` which allows to declare a filename where the scraped
items will be written.

Another important feature is the `save_item` method of the [StaticSpider](api.md#greenstaticspider) which appends a new
item in the `Configuration.backup_filename` file. Messages are serialized using `msgpack` which help to serialize complex
data types like `list` or `dict` in a fast way. So here is what we can do to save all quote information.

With gevent:

```python
from scalpel import Configuration
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        spider.save_item(data)

config = Configuration(backup_filename='/path/to/file.mp')  # write a true path
static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse, config=config)
static_spider.run()
```

With trio:

```python
import trio
from scalpel import Configuration
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        await spider.save_item(data)

async def main() -> None:
    config = Configuration(backup_filename='/path/to/file.mp')  # write a true path here
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse, config=config)
    await spider.run()

trio.run(main)
```

!!! note
    You don't necessarily have to specify a backup file. A default one is created for you in the form `backup-<uuid>.mp`
    where `<uuid>` represents a random [UUID](https://tools.ietf.org/html/rfc4122.html) value. 

Now we are done, but.. wait a minute! How will we read the file we just created? Since we use `msgpack` to serialize
objects the builtin `open` function will be useless. This is where pyscalpel [msgpack utilities](api.md#msgpack) come in
handy. Here is how you can read a file created by your spider.

With gevent:

```python
from scalpel.green import read_mp

for quote in read_mp('/path/to/file.mp'):
    print(quote)
```

With trio:

```python
import trio
from scalpel.trionic import read_mp

async def main() -> None:
    async for quote in read_mp('/path/to/file.mp'):
        print(quote)

trio.run(main)
```

Yeah! Now we have useful data that we can exploit.

## Going further

In the previous part we wrote a spider to scrape all quotes on the first page of 
[quotes.toscrape](https://quotes.toscrape.com). This is already a good step but we might want to go further and 
retrieved all quote information on the website. We need a way to *follow* the link on the next page and process it.
For that the `StaticSpider.follow` method helps us. 

So if we look closely at the HTML structure of the website, we notice that the link to the next page is referenced like
this:

```html
<nav>
    <ul class="pager">
        <li class="next">
            <a href="/page/2/">Next <span aria-hidden="true">&rarr;</span></a>
        </li>
    </ul>
</nav>
```

So this is what we can do to get all website quote data.

With gevent:

```python
from scalpel import Configuration
from scalpel.green import StaticResponse, StaticSpider

def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        spider.save_item(data)

    next_link = response.xpath('//nav/ul/li[@class="next"]/a').xpath('@href').get()
    if next_link is not None:
        response.follow(next_link)

config = Configuration(backup_filename='data.mp')
static_spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse, config=config)
static_spider.run()
# we print some statistics about the crawl operation
print(static_spider.statistics())
```

With trio:

```python
import trio
from scalpel import Configuration
from scalpel.trionic import StaticResponse, StaticSpider

async def parse(spider: StaticSpider, response: StaticResponse) -> None:
    for quote in response.xpath('//div[@class="quote"]'):
        data = {
            'message': quote.xpath('./span[@class="text"]/text()').get(),
            'author': quote.xpath('./span/small/text()').get(),
            'tags': quote.xpath('./div/a/text()').getall()
        }
        await spider.save_item(data)
    
    next_link = response.xpath('//nav/ul/li[@class="next"]/a').xpath('@href').get()
    if next_link is not None:
        await response.follow(next_link)


async def main() -> None:
    config = Configuration(backup_filename='data.mp')
    spider = StaticSpider(urls=['https://quotes.toscrape.com'], parse=parse, config=config)
    await spider.run()
    # we print some statistics about the crawl operation
    print(spider.statistics())

trio.run(main)
```

There we goo! So now, if you read the file created, *data.mp* in the example case, you will get all quote information from
the first page to the last page. Don't hesitate to look at the 
[examples](https://github.com/lewoudar/scalpel/tree/master/examples) folder for more code snippets to view.

Some important notes:

* In the previous code, we check if the link we want to follow exists, `if next_link is not None`, it is important because
on the [last](https://quotes.toscrape.com/page/10/) page there is no next link 😛
* On the last line I printed spider [statistics](api.md#spiderstatistics) which contains many information like the total
time taken by the spider, urls scrapped, followed or rejected due to robots.txt rules. You will probably need these 
information at some point in time.

## Good to know

pyscalpel can also deals with file urls instead of http ones. The url needs to start with `file:///` followed by the
file path. You can use [Path.as_uri](https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.as_uri) method
to help you to create these urls.

You will notice that the following spider attributes are public and therefore can be set in the *parse* function:

* reachable_urls
* unreachable_uls
* robot_excluded_urls
* followed_urls
* request_counter

The reason is that when running (very) long crawlers, it can be useful to empty these sets to avoid running
out of memory and set counter to 0 to be in sync with the sets. Please **do not abuse** of this possibility and only
use it when appropriate.

If you want a more object-oriented approach for your spider than a function, you can always use a class. Just remember
that the parse attribute of the `StaticSpider` waits for a callable. An example:

With gevent:

```python
from scalpel.green import StaticSpider, StaticResponse


class Parser:

    def __call__(self, spider: StaticSpider, response: StaticResponse) -> None:
        print(response.text)


spider = StaticSpider(urls=['http://quotes.toscrape.com'], parse=Parser())
spider.run()
```

With trio:

```python
import trio
from scalpel.trionic import StaticResponse, StaticSpider


class Parser:
    
    async def __call__(self, spider: StaticSpider, response: StaticResponse) -> None:
        print(response.text)

async def main():
    spider = StaticSpider(urls=['http://quotes.toscrape.com'], parse=Parser())
    await spider.run()

trio.run(main)
```