"""
文件名: EmailSenderExample.py
作者: yangchunhui
创建日期: 2026/2/9
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/9 15:30
描述: BaseEmailSender 使用示例，展示如何使用邮件发送器发送各种类型的邮件

修改历史:
2026/2/9 15:30 - yangchunhui - 初始版本

依赖:
- common.utils.email.BaseEmailSender: 邮件发送基类
- os: 环境变量读取
"""

import os
import asyncio
from common.utils.func.email.BaseEmailSender import BaseEmailSender, EmailSendError


async def example_basic_usage():
    """基础使用示例"""
    # 从环境变量读取配置
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER", "smtp.exmail.qq.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL","support.berry@blueberryintelligence.com"),
        sender_password=os.getenv("SENDER_PASSWORD","awPPqTAnp56bhanY"),
        sender_name="系统通知",
        use_ssl=True
    )

    try:
        # 发送纯文本邮件
        await sender.send_text_email(
            to="2609060093@qq.com",
            subject="测试邮件",
            content="这是一封测试邮件"
        )
        print("✓ 纯文本邮件发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


async def example_html_email():
    """发送 HTML 邮件示例"""
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER", "smtp.exmail.qq.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL", "support.berry@blueberryintelligence.com"),
        sender_password=os.getenv("SENDER_PASSWORD", "awPPqTAnp56bhanY"),
        sender_name="系统通知",
        use_ssl=True
    )

    html_content = """
    <html>
        <body>
            <h1>欢迎注册</h1>
            <p>您的验证码是：<strong style="color: red;">123456</strong></p>
            <p>验证码有效期为 10 分钟</p>
        </body>
    </html>
    """

    try:
        await sender.send_html_email(
            to="2609060093@qq.com",
            subject="注册验证码",
            html_content=html_content
        )
        print("✓ HTML 邮件发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


async def example_multiple_recipients():
    """发送给多个收件人示例"""
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL"),
        sender_password=os.getenv("SENDER_PASSWORD")
    )

    try:
        await sender.send_text_email(
            to=["user1@example.com", "user2@example.com"],
            subject="团队通知",
            content="这是发送给多人的邮件",
            cc="manager@example.com",  # 抄送给经理
            bcc="admin@example.com"    # 密送给管理员
        )
        print("✓ 多收件人邮件发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


async def example_email_with_attachments():
    """发送带附件的邮件示例"""
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL"),
        sender_password=os.getenv("SENDER_PASSWORD")
    )

    try:
        await sender.send_email_with_attachments(
            to="receiver@example.com",
            subject="月度报告",
            content="<h2>请查收本月报告</h2><p>详见附件</p>",
            attachments=[
                "/path/to/report.pdf",
                "/path/to/data.xlsx"
            ],
            is_html=True
        )
        print("✓ 带附件邮件发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


async def example_customer_inquiry_notification():
    """实际业务场景：客户咨询通知"""
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL"),
        sender_password=os.getenv("SENDER_PASSWORD"),
        sender_name="客户服务系统"
    )

    # 客户信息
    customer_data = {
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800138000",
        "message": "我想了解贵公司的产品详情",
        "time": "2026-02-09 15:30:00"
    }

    # 构建 HTML 内容
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .info {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>新客户咨询通知</h2>
                </div>
                <div class="content">
                    <div class="info">
                        <span class="label">客户姓名：</span>{customer_data['name']}
                    </div>
                    <div class="info">
                        <span class="label">联系邮箱：</span>{customer_data['email']}
                    </div>
                    <div class="info">
                        <span class="label">联系电话：</span>{customer_data['phone']}
                    </div>
                    <div class="info">
                        <span class="label">咨询时间：</span>{customer_data['time']}
                    </div>
                    <div class="info">
                        <span class="label">咨询内容：</span>
                        <p>{customer_data['message']}</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    try:
        await sender.send_html_email(
            to="sales@company.com",
            subject=f"新客户咨询 - {customer_data['name']}",
            html_content=html_content,
            cc="manager@company.com"
        )
        print("✓ 客户咨询通知发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


async def example_verification_code():
    """实际业务场景：发送验证码"""
    sender = BaseEmailSender(
        smtp_server=os.getenv("SMTP_SERVER"),
        smtp_port=int(os.getenv("SMTP_PORT", "465")),
        sender_email=os.getenv("SENDER_EMAIL"),
        sender_password=os.getenv("SENDER_PASSWORD"),
        sender_name="账号安全中心"
    )

    verification_code = "123456"

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; border: 1px solid #ddd; padding: 20px;">
                <h2 style="color: #333;">验证码</h2>
                <p>您正在进行账号验证，验证码为：</p>
                <div style="background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; color: #e74c3c; letter-spacing: 5px;">
                    {verification_code}
                </div>
                <p style="color: #666; margin-top: 15px;">验证码有效期为 10 分钟，请勿泄露给他人。</p>
                <p style="color: #999; font-size: 12px;">如果这不是您的操作，请忽略此邮件。</p>
            </div>
        </body>
    </html>
    """

    try:
        await sender.send_html_email(
            to="user@example.com",
            subject="您的验证码",
            html_content=html_content
        )
        print("✓ 验证码邮件发送成功")

    except EmailSendError as e:
        print(f"✗ 邮件发送失败: {e}")


if __name__ == "__main__":
    # 运行示例
    print("=== 邮件发送示例 ===\n")

    # 选择要运行的示例
    # asyncio.run(example_basic_usage())
    asyncio.run(example_html_email())
    # asyncio.run(example_multiple_recipients())
    # asyncio.run(example_email_with_attachments())
    # asyncio.run(example_customer_inquiry_notification())
    # asyncio.run(example_verification_code())
