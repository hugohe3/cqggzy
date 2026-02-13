import unittest

from common.parser import parse_api_records, parse_detail_html


class ParserTests(unittest.TestCase):
    def test_parse_api_records_with_json_string_content(self):
        api_data = {
            "code": 200,
            "content": '{"result": {"records": [{"title": "a"}], "totalcount": "1"}}',
        }
        records, total = parse_api_records(api_data)
        self.assertEqual(1, len(records))
        self.assertEqual(1, total)

    def test_parse_api_records_with_invalid_json_content(self):
        api_data = {"code": 200, "content": "{bad json"}
        records, total = parse_api_records(api_data)
        self.assertEqual([], records)
        self.assertEqual(0, total)

    def test_parse_detail_html_extracts_basic_fields(self):
        html = """
        <html>
          <body>
            <h2 class="detail-title">测试公告</h2>
            <table>
              <tr><td>采购人：</td><td>重庆某单位</td></tr>
            </table>
            <div class="article-content">
              一、成交金额：100万元
            </div>
          </body>
        </html>
        """
        parsed = parse_detail_html(html)
        self.assertEqual("测试公告", parsed.get("页面标题"))
        self.assertEqual("重庆某单位", parsed.get("采购人"))
        self.assertEqual("100万元", parsed.get("成交金额"))
        self.assertIn("正文内容", parsed)


if __name__ == "__main__":
    unittest.main()
