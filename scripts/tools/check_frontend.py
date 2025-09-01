#!/usr/bin/env python3
"""
使用 Playwright 检查前端数据显示问题
"""

import asyncio
from playwright.async_api import async_playwright


async def check_data_display():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("🔍 正在检查前端数据显示问题...")

        # 导航到数据页面
        await page.goto("http://127.0.0.1:8000")
        await page.wait_for_load_state("networkidle")

        # 点击数据查看页面
        print("📊 切换到数据查看页面...")
        await page.click("text=数据查看")
        await page.wait_for_timeout(2000)

        # 检查页面是否正确加载
        data_title = await page.text_content("h3")
        print(f"页面标题: {data_title}")

        # 检查查询表单
        station_select = await page.query_selector("#stationSelect")
        device_select = await page.query_selector("#deviceSelect")

        print(f'泵站选择器: {"存在" if station_select else "缺失"}')
        print(f'设备选择器: {"存在" if device_select else "缺失"}')

        # 获取泵站选项
        if station_select:
            station_options = await page.evaluate(
                """() => {
                const select = document.getElementById("stationSelect");
                return Array.from(select.options).map(opt => opt.text);
            }"""
            )
            print(f"泵站选项: {station_options}")

        # 执行查询
        print("\n🔍 执行数据查询...")
        query_button = await page.query_selector('button:has-text("查询")')
        if query_button:
            await query_button.click()
            await page.wait_for_timeout(3000)

            # 检查数据表格
            data_table = await page.query_selector("#dataTable table")
            if data_table:
                # 获取表格行数
                rows = await page.query_selector_all("#dataTable table tbody tr")
                print(f"数据行数: {len(rows)}")

                if rows:
                    # 检查第一行数据
                    first_row_data = await page.evaluate(
                        """() => {
                        const firstRow = document.querySelector("#dataTable table tbody tr:first-child");
                        if (!firstRow) return null;
                        const cells = firstRow.querySelectorAll("td");
                        return {
                            timestamp: cells[0]?.textContent?.trim(),
                            device_id: cells[1]?.textContent?.trim(),
                            flow_rate: cells[2]?.textContent?.trim(),
                            pressure: cells[3]?.textContent?.trim(),
                            power: cells[4]?.textContent?.trim(),
                            frequency: cells[5]?.textContent?.trim()
                        };
                    }"""
                    )

                    print("\n📋 第一行数据:")
                    for key, value in first_row_data.items():
                        has_value = (
                            value and value != "-" and "text-gray-400" not in value
                        )
                        status = "✅" if has_value else "❌"
                        print(f"  {status} {key}: {value}")

                    # 统计有效数据字段
                    valid_fields = sum(
                        1
                        for key, value in first_row_data.items()
                        if key not in ["timestamp", "device_id"]
                        and value
                        and value != "-"
                        and "text-gray-400" not in value
                    )
                    print(f"\n📊 数据完整性: {valid_fields}/4 个测量字段有值")

                    if valid_fields >= 3:
                        print("🎉 数据聚合修复成功！")
                    elif valid_fields >= 1:
                        print("⚠️ 部分数据显示正常，但仍需优化")
                    else:
                        print("❌ 数据显示仍有问题")

                    # 检查更多行的数据
                    print("\n🔍 检查前5行数据的完整性...")
                    for i in range(min(5, len(rows))):
                        row_data = await page.evaluate(
                            f"""() => {{
                            const row = document.querySelector("#dataTable table tbody tr:nth-child({i+1})");
                            if (!row) return null;
                            const cells = row.querySelectorAll("td");
                            const flowCell = cells[2]?.textContent?.trim();
                            const pressureCell = cells[3]?.textContent?.trim();
                            const powerCell = cells[4]?.textContent?.trim();
                            const freqCell = cells[5]?.textContent?.trim();

                            const validCount = [flowCell, pressureCell, powerCell, freqCell]
                                .filter(v => v && v !== '-' && !v.includes('text-gray-400')).length;
                            return {{ validCount, total: 4 }};
                        }}"""
                        )

                        if row_data:
                            print(
                                f'  行 {i+1}: {row_data["validCount"]}/{row_data["total"]} 字段有值'
                            )
                else:
                    print("❌ 没有数据行")
            else:
                print("❌ 未找到数据表格")
        else:
            print("❌ 未找到查询按钮")

        await browser.close()


# 运行检查
if __name__ == "__main__":
    asyncio.run(check_data_display())
