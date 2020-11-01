# Selenium spider


## Foreword

Nowadays many websites heavily used [AJAX](https://en.wikipedia.org/wiki/Ajax_(programming)) techniques to load their
pages. There is a movement with the advent of new frontend (javascript) frameworks like [react](https://reactjs.org/),
[vue](https://v3.vuejs.org/guide/introduction.html) or [svelte](https://svelte.dev/) that allow to create
[SPA](https://en.wikipedia.org/wiki/Single-page_application) applications and unfortunately static spiders become
useless.

Let's see an example with [httpbin](http://httpbin.org/) to understand what the implications are. This website is a SPA
created with [react](https://reactjs.org/). For information, this website provides a simple interface to play with
HTTP requests (testing your http client). If you click on the *HTTP methods* menu, you will see five requests you can
make. Ok now look at the HTML source with `ctrl + u` and you will see... almost nothing if not weird information. 
The reason is simple, the page is loaded via [javascript](https://en.wikipedia.org/wiki/JavaScript), in other words
almost all content is loaded dynamically after the page is fetched. Now right click on the menu *HTTP methods* and click
*Inspect Element* (or *Inspect* depending on your browser), you will see the HTML related to this menu :)

I will not do a course on browser dev tools, there are many resources on the web but this is basically how you can 
inspect the HTML source of SPA applications.

Like I said early static spiders are useless in the case of SPA applications because the inner 
[httpx](https://www.python-httpx.org/) client they rely on do not know how to deal with javascript loading.
So how can we scrape data from SPA applications? There are not many choices here, we need a browser! And we don't only
need a browser but also a tool able to handle a browser without human interaction commonly called a *driver*.

!!! note
    Every browser has a specific driver so you need to install one for the browser you use.

This is where [selenium](https://selenium-python.readthedocs.io/) comes in. It is a python library able to control
browser via the use of *drivers*. The [installation](https://selenium-python.readthedocs.io/installation.html) section
is not very detailed about how to install browser drivers. Although you can find resources on the web on this, here are
some tips:

* For Windows users, the simplest thing to do is to install your driver via [chocolatey](https://chocolatey.org/). It is
an awesome package manager for Windows. Just search *selenium* on the 
[packages](https://chocolatey.org/packages?q=selenium) page and you will see all drivers available and instructions to
install them.
* For Mac OS users, the installation is also really simple via [homebrew](https://brew.sh/index_fr) 
an awesome package manager for Mac OS. You can for example install *chromedriver* with `brew cask install chromedriver`.
To search for a specific driver, refer to the different [packages](https://formulae.brew.sh/) pages.
* For linux users, well.. this is probably the most complicated. There are many ways to do depending on the OS you
are using, unfortunately I can't give you an all-in-one solution. Nevertheless, for ubuntu users here is a 
[recipe](https://gist.github.com/ziadoz/3e8ab7e944d02fe872c3454d17af31a5) to install chrome and his driver, and here 
is a [forum question](https://askubuntu.com/questions/870530/how-to-install-geckodriver-in-ubuntu) with a way to install
*geckodriver* (take care to update the version used in the example).

## Configuration

There are some [Configuration](api.md#configuration) attributes related to a selenium spider that you should be aware of:

* `selenium_find_timeout`: this indicates the number of seconds `selenium` should wait to search for a DOM element.
* `selenium_browser`: a [Browser](api.md#browser) enum to indicate the underlying browser used by selenium. Only two
values are possible for now, `FIREFOX` for the firefox browser and `CHROME` for the chrome browser. Defaults to 
`FIREFOX`, so if you are using chrome make sure to change this attribute.
* `selenium_driver_log_file`: A path to a file were browser drivers will write debug information. Defaults to 
`driver.log`. You can set it to `None` if you don't want this log file.
* `selenium_driver_executable_path`: the path to the driver executable used by the spider. Defaults to `geckodriver` for
firefox and `chromedriver` for chrome. If for some reason, you don't add the driver executable in your `PATH`
environment, **you must set this attribute** with the right path.

## Our first selenium spider

First of all, I will not teach how to use the `selenium` library, if you don't know it, you can read this
[introduction](https://selenium-python.readthedocs.io/getting-started.html). Many concepts of the static spider will be
reused for the selenium spider so if you don't read the static spider [guide](static-spider.md), it is a good idea to do
so before continuing here.

So if we come back to [httpbin](http://httpbin.org/), let's say we want to scrape the menu title plus a description
of all the methods related to this menu. If we look at the HTML source of a menu with a browser dev tool, we can see
that the structure is like the following:

```html
<div class="opblock-tag-section">
    <h4 class="opblock-tag" id="operations-tag-HTTP_Methods">
        <a class="nostyle" href="#/HTTP Methods"><span>HTTP Methods</span></a>
        <small>
            <div class="markdown">Testing different HTTP verbs</div>
        </small>
        <div style="height: auto; border: none; margin: 0px; padding: 0px;">
            <!-- react-text: 451 --> <!-- /react-text -->
            <div class="opblock opblock-delete" id="operations-HTTP Methods-delete_delete">
                <div class="opblock-summary opblock-summary-delete">
                    <span class="opblock-summary-method">DELETE</span>
                    <span class="opblock-summary-path">
                    <a class="nostyle" href="#/operations/HTTP Methods/delete_delete">
                        <span>/delete</span>
                    </a><!-- react-empty: 458 --><!-- react-text: 459 --> <!-- /react-text -->
                </span>
                    <div class="opblock-summary-description">The request's DELETE parameters.</div>
                </div>
                <noscript></noscript>
            </div>
            ...
            <button class="expand-operation" title="Expand operation">
                <svg class="arrow" width="20" height="20">
                    <use href="#large-arrow" xlink:href="#large-arrow"></use>
                </svg>
            </button>
        </div>    
    </h4>
    <noscript></noscript>
</div>
```
We see that the menu title is in a `h4` tag. The description of the methods is inside a 
`<div class="opblock XXX">..</div>` and inside it we have: 

* the method name in a `<span class="opblock-summary-method"..>..</span>`
* the route path in a `span[class="opblock-summary-path]/a/span`
* the method description in `<span class="opblock-summary-description">..</span>`

So this is what we can write to scrape all menu information on the website.

With gevent:

```python
from scalpel.green import SeleniumResponse, SeleniumSpider

def parse(_, response: SeleniumResponse) -> None:
    for block in response.driver.find_elements_by_xpath('//div[@class="opblock-tag-section"]'):
        block.click()
        h4_text = block.find_element_by_xpath('./h4').text
        title, description = h4_text.split('\n')
        print('****', title, '****')
        print(description)
        print('=== operations ===')

        methods = (method.text for method in block.find_elements_by_xpath('.//span[@class="opblock-summary-method"]'))
        paths = (path.text for path in block.find_elements_by_xpath('.//span[@class="opblock-summary-path"]/a/span'))
        descriptions = (description.text for description in
                        block.find_elements_by_xpath('.//div[@class="opblock-summary-description"]'))
        for method, path, description in zip(methods, paths, descriptions):
            print('\tmethod:', method)
            print('\tpath:', path)
            print('\tdescription:', description, end='\n\n')


# the default browser used is firefox, if you are using chrome, don't forget to set the configuration like this
# config = Configuration(selenium_browser=Browser.CHROME)
# and the instantiate the spider using the config attribute
# spider = SeleniumSpider(urls=['http://httpbin.org/'], parse=parse, config=config)
spider = SeleniumSpider(urls=['http://httpbin.org/'], parse=parse)
spider.run()
```

With trio:

```python
import trio
from scalpel.trionic import SeleniumSpider, SeleniumResponse

async def parse(_, response: SeleniumResponse) -> None:
    for block in response.driver.find_elements_by_xpath('//div[@class="opblock-tag-section"]'):
        block.click()
        h4_text = block.find_element_by_xpath('./h4').text
        title, description = h4_text.split('\n')
        print('****', title, '****')
        print(description)
        print('=== operations ===')

        methods = (method.text for method in block.find_elements_by_xpath('.//span[@class="opblock-summary-method"]'))
        paths = (path.text for path in block.find_elements_by_xpath('.//span[@class="opblock-summary-path"]/a/span'))
        descriptions = (description.text for description in
                        block.find_elements_by_xpath('.//div[@class="opblock-summary-description"]'))
        for method, path, description in zip(methods, paths, descriptions):
            print('\tmethod:', method)
            print('\tpath:', path)
            print('\tdescription:', description, end='\n\n')

async def main() -> None:
    # the default browser used is firefox, if you are using chrome, don't forget to set the configuration like this
    # config = Configuration(selenium_browser=Browser.CHROME)
    # and the instantiate the spider using the config attribute
    # spider = SeleniumSpider(urls=['http://httpbin.org/'], parse=parse, config=config)
    spider = SeleniumSpider(urls=['http://httpbin.org/'], parse=parse)
    await spider.run()

trio.run(main)
```

You will have an output similar to the following:

```sh
**** HTTP Methods ****
Testing different HTTP verbs
=== operations ===
	method: DELETE
	path: /delete
	description: The request's DELETE parameters.

	method: GET
	path: /get
	description: The request's query parameters.

	method: PATCH
	path: /patch
	description: The request's PATCH parameters.

	method: POST
	path: /post
	description: The request's POST parameters.

	method: PUT
	path: /put
	description: The request's PUT parameters.

**** Auth ****
...
```

Some notes:

* the first obvious changes are the uses of `SeleniumSpider` and `SeleniumResponse` instead of `StaticSpider` and
`StaticResponse`. The usage of `SeleniumSpider` will not differ from `StaticSpider` but for the 
[SeleniumResponse](api.md#greenseleniumresponse) class there are no more `css` and `xpath` methods. 
Instead we have a `drive` attribute which represents a selenium `WebDriver` object and will be used to interact with
the browser.
* You may have noticed usage of `_` in the definition of the parse function `parse(_, response: SeleniumResponse)` 
this is because I don't use the spider object in the function body so I mark it explicitly. It is a good practice in
my opinion.
* The `driver` attribute is a selenium webdriver object where we can apply a lot of methods like `find_elements_by_xpath`
which look familiar to the `StaticResponse.xpath` method. You can look at the entire webdriver api 
[here](https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webdriver.html).
* Do not hesitate to look at the [examples](https://github.com/lewoudar/scalpel/tree/master/examples) 
for more code snippets to view.

!!! danger
    Please do not call `close` or `quit` methods of the driver object because this will certainly crashed your
    application. The resource closing is done by scalpel.


## Caveats

Integration of selenium in scalpel is not optimal because of the synchronous nature of selenium and the fact that
selenium does not have a notion of a *tab* object. You only handle one window tab at a time. All of this make it hard to
combine selenium with asynchronous frameworks such as `gevent` or `trio`. The direct consequence of it is that
**asynchronous operations** such as `follow`, `save_item` or whatever asynchronous api you use **must** be done at the
end of your parse callable. You can't mix them up anywhere in the code. For example:

With gevent:

```python
from scalpel.green import StaticResponse

def parse(_, response: StaticResponse) -> None:
    response.xpath('//p')
    response.follow('/page/2')  # not good
    # the reason is that for now scalpel cannot guaranteed that the next line 
    # will be executed on the page you expected
    response.xpath('//div')
```

With trio:

```python
from scalpel.trionic import StaticResponse

async def parse(_, response: StaticResponse) -> None:
    response.xpath('//p')
    await response.follow('/page/2')  # not good
    # the reason is that for now scalpel cannot guaranteed that the next line 
    # will be executed on the page you expected
    response.xpath('//div')
```

Instead you should perform all your code scraping, parsing before running asynchronous operations.

With gevent:

```python
from scalpel.green import StaticResponse

def parse(_, response: StaticResponse) -> None:
    response.xpath('//p')
    response.xpath('//div')
    response.follow('/page/2')  # good
```

With trio:

```python
from scalpel.trionic import StaticResponse

async def parse(_, response: StaticResponse) -> None:
    response.xpath('//p')
    response.xpath('//div')
    await response.follow('/page/2')  # good
```

Another direct consequence of the bad asynchronous integration of selenium is that if you follow urls you will notice
that the behaviour is more sequential than concurrent with regard to url handling. Nevertheless the selenium spider
is still useful (if you respect the previous advice), just slow for now.