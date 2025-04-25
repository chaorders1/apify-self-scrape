"""
Apify Store Actors Scraper

这个脚本使用Playwright自动化浏览器抓取https://apify.com/store/categories?sortBy=popularity页面中的所有actors。
页面使用连续滚动加载更多内容，使用渐进式滚动来模拟人的行为，直到所有actors都被加载出来。

输出将保存为CSV文件，包含以下信息：
- 标题
- 作者名称
- 用户数
- 评分
- 描述
- 链接
"""

import time
import csv
import asyncio
import random
from playwright.async_api import async_playwright
import pandas as pd
from typing import List, Dict, Any
import logging
import re
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def random_sleep(min_seconds=1, max_seconds=3):
    """
    随机等待一段时间，模拟人类行为
    
    Args:
        min_seconds (float): 最短等待时间
        max_seconds (float): 最长等待时间
    """
    wait_time = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(wait_time)


async def gradual_scroll(page, step=300, delay_min=0.1, delay_max=0.5):
    """
    渐进式滚动，更像人类的浏览行为
    
    Args:
        page: Playwright页面对象
        step (int): 每次滚动的像素高度
        delay_min (float): 每次滚动的最小延迟
        delay_max (float): 每次滚动的最大延迟
    """
    # 获取当前滚动位置
    current_scroll = await page.evaluate('window.scrollY')
    # 获取页面高度
    body_height = await page.evaluate('document.body.scrollHeight')
    
    # 计算需要滚动多少步以到达底部
    target_position = min(current_scroll + 1200, body_height - 800)  # 留出一些空间，不完全滚到底
    
    # 渐进式滚动
    while current_scroll < target_position:
        current_scroll = min(current_scroll + step, target_position)
        await page.evaluate(f'window.scrollTo(0, {current_scroll})')
        await random_sleep(delay_min, delay_max)
    
    # 最后暂停一会儿，让内容加载
    await random_sleep(0.5, 1.5)
    
    return current_scroll >= (body_height - 1000)  # 如果接近底部，返回True


async def scrape_actors() -> List[Dict[str, Any]]:
    """
    抓取Apify商店中的所有actors
    
    Returns:
        List[Dict[str, Any]]: 包含所有actors信息的列表
    """
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)  # headless=False用于调试
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 打开新页面
        page = await context.new_page()
        
        # 访问目标页面 - 使用新的URL
        target_url = "https://apify.com/store/categories?sortBy=popularity"
        logger.info(f"正在访问{target_url}...")
        await page.goto(target_url, timeout=60000)
        
        # 等待页面加载
        await page.wait_for_selector('[data-test="actor-card"]', timeout=30000)
        
        # 尝试获取预期的actors总数
        logger.info("尝试获取总数...")
        total_count = None  # 初始化为 None，不再硬编码
        extracted_count_str = "未知"
        
        try:
            # 尝试获取显示总数的元素
            page_text = await page.evaluate('() => document.body.innerText')
            matches = re.findall(r'(\d{1,4}(?:,\d{3})*)\s*actors', page_text)
            if matches:
                total_count_str = matches[0].replace(',', '')
                total_count = int(total_count_str)
                extracted_count_str = str(total_count)
                logger.info(f"从页面文本中提取到总数: {total_count}")
            else:
                logger.warning("未能从页面文本中提取到总数。")
        except Exception as e:
            logger.error(f"获取总数时出错: {str(e)}")
            logger.warning("无法提取总数。")
        
        logger.info(f"预期抓取的actors总数 (供参考): {extracted_count_str}")
        
        # 存储抓取到的actors
        actors = []
        previously_loaded_count = 0
        no_new_items_count = 0
        no_new_items_threshold = 15  # 增加连续无新内容加载的阈值
        max_attempts = 350
        attempt = 0
        loop_termination_reason = "达到最大尝试次数" # Default reason
        
        logger.info("开始滚动页面加载所有actors...")
        while attempt < max_attempts:
            attempt += 1
            
            # 渐进式滚动，更像人类行为
            is_near_bottom = await gradual_scroll(page)
            
            # 获取当前页面上的所有actor卡片
            cards = await page.query_selector_all('[data-test="actor-card"]')
            current_card_count = len(cards)
            
            logger.info(f"当前页面上找到 {current_card_count} 个actor卡片")
            
            # 检查是否有新内容加载
            if current_card_count == previously_loaded_count:
                no_new_items_count += 1
                logger.info(f"连续 {no_new_items_count}/{no_new_items_threshold} 次滚动没有加载新内容...")

                if no_new_items_count >= 5: # 保留原有5次后的交互逻辑
                    logger.info(f"尝试模拟交互以触发加载...")
                    # 随机移动鼠标，更像人类行为
                    x = random.randint(100, 1000)
                    y = random.randint(100, 600)
                    await page.mouse.move(x, y)
                    
                    # 更剧烈地滚动一下，触发加载
                    await page.evaluate('window.scrollBy(0, 1000)')
                    await random_sleep(1, 2)
                    
                    # 如果已接近底部但无新内容，尝试点击"加载更多"按钮（如果存在）
                    if is_near_bottom:
                        try:
                            load_more_selector = "button:has-text('Load more'), button:has-text('加载更多')"
                            load_more_button = await page.query_selector(load_more_selector)
                            if load_more_button:
                                logger.info("找到'加载更多'按钮，尝试点击...")
                                await load_more_button.click()
                                await random_sleep(2, 4)
                                no_new_items_count = 0  # 重置计数器
                            else:
                                # 尝试点击当前显示的分页按钮（如果存在）
                                pagination_next = await page.query_selector("button[aria-label='Next page']")
                                if pagination_next:
                                    logger.info("找到'下一页'按钮，尝试点击...")
                                    await pagination_next.click()
                                    await random_sleep(2, 4)
                                    no_new_items_count = 0  # 重置计数器
                                # 如果多次尝试后仍无法加载更多
                                if no_new_items_count >= no_new_items_threshold:
                                    logger.info(f"连续 {no_new_items_threshold} 次尝试没有加载新内容，停止抓取。")
                                    loop_termination_reason = f"连续{no_new_items_threshold}次无新项目"
                                    break # 跳出主循环
                        except Exception as e:
                            logger.error(f"尝试加载更多内容时出错: {str(e)}")
            else:
                no_new_items_count = 0  # 重置计数器
            
            previously_loaded_count = current_card_count
            
            # 处理当前可见的卡片
            for i, card in enumerate(cards):
                try:
                    # 检查这个卡片是否已经处理过
                    card_href = await card.get_attribute('href')
                    if any(actor.get('url') == card_href for actor in actors):
                        continue
                    
                    # 创建一个新的数据对象
                    actor_data = {'url': card_href}
                    
                    # 获取各种信息
                    # 尝试多种选择器来适应可能的页面结构变化
                    selectors = {
                        'title': ['.ActorStoreItem-title h3', 'h3', '[class*="title"] h3'],
                        'slug': ['.ActorStoreItem-slug', 'p[class*="slug"]', 'p:nth-child(2)'],
                        'description': ['.ActorStoreItem-desc', 'p[class*="desc"]', 'p:nth-child(3)'],
                        'author': ['.ActorStoreItem-user-fullname', 'p[class*="fullname"]', 'div[class*="author"] p']
                    }
                    
                    # 对每个字段尝试多个选择器
                    for field, selector_list in selectors.items():
                        for selector in selector_list:
                            element = await card.query_selector(selector)
                            if element:
                                actor_data[field] = await element.inner_text()
                                break
                        if field not in actor_data:
                            actor_data[field] = f"未找到{field}"
                    
                    # 获取用户数和评分 - 尝试多种方法
                    item_selectors = [
                        '.ActorStoreItem-item p', 
                        'div[class*="item"] p',
                        'div:has(> svg) p'
                    ]
                    
                    for selector in item_selectors:
                        item_elements = await card.query_selector_all(selector)
                        if len(item_elements) >= 1:
                            actor_data['users'] = await item_elements[0].inner_text()
                            if len(item_elements) >= 2:
                                actor_data['rating'] = await item_elements[1].inner_text()
                            break
                    
                    if 'users' not in actor_data:
                        actor_data['users'] = "未找到用户数"
                    if 'rating' not in actor_data:
                        actor_data['rating'] = "未找到评分"
                    
                    actors.append(actor_data)
                    
                    # 每处理10个卡片输出一次进度
                    if (len(actors) % 10 == 0):
                        logger.info(f"已处理 {len(actors)} 个actors")
                        
                except Exception as e:
                    logger.error(f"处理第 {i+1} 个卡片时出错: {str(e)}")
                    continue
            
            logger.info(f"已加载 {current_card_count} 个actors，已处理 {len(actors)} 个，目标总数 {total_count}，尝试次数 {attempt}/{max_attempts}")
            
            # 随机等待，模拟人类行为
            await random_sleep(1, 3)
            
            # 每10次滚动后，添加一个更长的暂停
            if attempt % 10 == 0:
                logger.info("添加更长的暂停...")
                await random_sleep(3, 6)
                
                # 每隔一段时间保存一次中间结果
                if actors and attempt % 20 == 0:
                    temp_filename = f"apify_actors_temp_{len(actors)}.csv"
                    save_to_csv(actors, temp_filename)
                    logger.info(f"已保存中间结果到 {temp_filename}")
            
            # 如果已经达到最大尝试次数，确保保存最终结果
            if attempt >= max_attempts:
                logger.info(f"已达到最大尝试次数 {max_attempts}，停止抓取")
                loop_termination_reason = f"达到最大尝试次数 ({max_attempts})"
                break # 虽然循环条件会处理，显式break更清晰
        
        # 添加循环终止原因日志
        logger.info(f"滚动循环结束，原因: {loop_termination_reason}")

        # 关闭浏览器前确保数据被保存
        if actors:
            final_temp_filename = f"apify_actors_final_{len(actors)}.csv"
            save_to_csv(actors, final_temp_filename)
            logger.info(f"抓取结束，已保存最终结果到 {final_temp_filename}")
        
        await browser.close()
        return actors


def save_to_csv(actors: List[Dict[str, Any]], filename: str = 'apify_actors.csv') -> None:
    """
    将抓取到的actors数据保存为CSV文件
    
    Args:
        actors (List[Dict[str, Any]]): 抓取到的actors数据
        filename (str, optional): 输出文件名. 默认为 'apify_actors.csv'.
    """
    if not actors:
        logger.warning("没有数据可保存")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(actors)
    
    # 保存为CSV
    df.to_csv(filename, index=False, encoding='utf-8')
    logger.info(f"数据已保存到 {filename}，共 {len(df)} 条记录")


async def main():
    """
    主函数
    """
    # 检查是否存在apify_actors.csv文件
    csv_filename = 'apify_actors.csv'
    if os.path.exists(csv_filename):
        logger.info(f"发现已存在的数据文件 {csv_filename}，正在加载...")
        try:
            df = pd.read_csv(csv_filename)
            actors = df.to_dict('records')
            logger.info(f"成功从文件加载了 {len(actors)} 个actors记录")
            
            # 显示数据摘要
            logger.info("\n数据摘要:")
            print(df.head().to_string())  # 使用print显示表格，logger会破坏格式
            logger.info(f"\n总共加载了 {len(df)} 条记录")
            return actors
        except Exception as e:
            logger.error(f"加载CSV文件时发生错误: {str(e)}")
            logger.info("将开始网络抓取流程...")
    else:
        logger.info(f"未找到数据文件 {csv_filename}，将开始网络抓取流程...")
    
    # 如果没有找到文件或加载失败，则执行原有的抓取流程
    logger.info("开始抓取Apify商店中的actors...")
    start_time = time.time()
    
    actors = await scrape_actors()
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"成功抓取了 {len(actors)} 个actors，耗时 {duration:.2f} 秒")
    
    # 保存数据
    save_to_csv(actors)
    
    # 显示数据摘要
    if actors:
        df = pd.DataFrame(actors)
        logger.info("\n数据摘要:")
        print(df.head().to_string())  # 使用print显示表格，logger会破坏格式
        logger.info(f"\n总共抓取了 {len(df)} 条记录")
    
    return actors


if __name__ == "__main__":
    try:
        actors = asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断了抓取过程")
        
        # 捕获键盘中断时，尝试保存已抓取的数据
        try:
            from asyncio import get_event_loop
            if 'actors' in locals() and actors:
                save_to_csv(actors, f"apify_actors_interrupted_{len(actors)}.csv")
                logger.info(f"已保存中断时的数据，共 {len(actors)} 条记录")
        except Exception as save_error:
            logger.error(f"保存中断数据时出错: {str(save_error)}")
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {str(e)}")
        raise 