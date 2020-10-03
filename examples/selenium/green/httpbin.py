from datetime import datetime
from pathlib import Path

from scalpel import Configuration, datetime_decoder
from scalpel.green import SeleniumSpider, SeleniumResponse, read_mp


def parse(spider: SeleniumSpider, response: SeleniumResponse) -> None:
    for block in response.driver.find_elements_by_xpath('//div[@class="opblock-tag-section"]'):
        block.click()
        h4_text = block.find_element_by_xpath('./h4').text
        title, description = h4_text.split('\n')
        result = {
            'title': title,
            'description': description,
            'operations': []
        }

        methods = (method.text for method in block.find_elements_by_xpath('.//span[@class="opblock-summary-method"]'))
        paths = (path.text for path in block.find_elements_by_xpath('.//span[@class="opblock-summary-path"]/a/span'))
        descriptions = (description.text for description in
                        block.find_elements_by_xpath('.//div[@class="opblock-summary-description"]'))
        for method, path, description in zip(methods, paths, descriptions):
            result['operations'].append({
                'method': method,
                'path': path,
                'description': description
            })
        spider.save_item(result)


def date_processor(item: dict) -> dict:
    item['date'] = datetime.now()
    return item


if __name__ == '__main__':
    backup = Path(__file__).parent / 'backup.mp'
    config = Configuration(selenium_driver_log_file=None, backup_filename=f'{backup}', item_processors=[date_processor])
    sel_spider = SeleniumSpider(urls=['http://httpbin.org/'], parse=parse, config=config)
    sel_spider.run()
    print(sel_spider.statistics())
    # you can do whatever you want with the results
    for quote_data in read_mp(filename=backup, decoder=datetime_decoder):
        print('****', quote_data['title'], '****')
        print(quote_data['description'])
        print('== operations ==')
        for operation in quote_data['operations']:
            print('\tmethod:', operation['method'])
            print('\tpath:', operation['path'])
            print('\tdescription:', operation['description'])
        print()
