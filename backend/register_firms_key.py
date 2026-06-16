"""
NASA FIRMS API Key 注册辅助
=============================
FIRMS (Fire Information for Resource Management System) 是全球最权威的
卫星火点监测系统，由 NASA 免费提供。

获取 API Key（免费，即时生效）:
1. 浏览器打开: https://firms.modaps.eosdis.nasa.gov/api/map_key/
2. 输入邮箱，勾选同意条款，点击 "Request API Key"
3. 收到的 key 是 32 位字符串，复制到本目录的 .env 文件中:
   FIRMS_API_KEY=你收到的key

注册后，系统将自动每小时拉取波斯湾区域真实火点数据。
"""
import webbrowser
import sys

def main():
    print(__doc__)
    url = "https://firms.modaps.eosdis.nasa.gov/api/map_key/"
    print(f"\n正在打开注册页面...")
    try:
        webbrowser.open(url)
    except Exception:
        print(f"请手动打开: {url}")

    print("\n获取 key 后，编辑 backend/.env:")
    print("  FIRMS_API_KEY=你的32位key")
    print("\n然后重启后端即可自动获取真实火点数据。")

if __name__ == "__main__":
    main()
