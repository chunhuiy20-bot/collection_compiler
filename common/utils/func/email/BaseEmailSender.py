"""
文件名: BaseEmailSender.py
作者: yangchunhui
创建日期: 2026/2/9
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/9 15:30
描述: 通用邮件发送基类，提供简单、通用的邮件发送功能。支持纯文本、HTML、附件发送，遵循单一职责原则，易于扩展和测试。

修改历史:
2026/2/9 15:30 - yangchunhui - 初始版本

依赖:
- smtplib: SMTP 邮件发送
- email: 邮件内容构建
- typing: 类型注解
- pathlib: 文件路径处理
- os: 环境变量读取

使用示例:
    详细请见EmailSenderExample
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from email.utils import formataddr
from typing import Optional, List, Union
from pathlib import Path
import asyncio
from common.utils.decorators.AsyncDecorators import async_retry


class EmailSendError(Exception):
    """邮件发送异常"""
    pass


class EmailConfig:
  """邮件配置类"""
  def __init__(
      self,
      smtp_server: str,
      smtp_port: int,
      sender_email: str,
      sender_password: str,
      sender_name: Optional[str] = None,
      use_ssl: bool = True
  ):
      self.smtp_server = smtp_server
      self.smtp_port = smtp_port
      self.sender_email = sender_email
      self.sender_password = sender_password
      self.sender_name = sender_name or sender_email
      self.use_ssl = use_ssl

class BaseEmailSender:
    """
    通用邮件发送器基类

    职责：
    1. 管理 SMTP 连接配置
    2. 提供邮件发送的基础方法
    3. 处理邮件格式转换
    """

    def __init__(self, config: EmailConfig):
        """
        初始化邮件发送器

        Args:
            config: 邮件配置对象
        """
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """验证配置"""
        if not all([self.config.smtp_server, self.config.smtp_port, self.config.sender_email, self.config.sender_password]):
            raise ValueError("SMTP 配置不完整，请检查必填参数")

    def _create_message(
        self,
        to: Union[str, List[str]],
        subject: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None
    ) -> MIMEMultipart:
        """
        创建邮件消息对象

        Args:
            to: 收件人（单个或多个）
            subject: 邮件主题
            cc: 抄送（可选）
            bcc: 密送（可选）

        Returns:
            MIMEMultipart 对象
        """
        message = MIMEMultipart()
        message['From'] = formataddr((self.config.sender_name, self.config.sender_email))
        message['To'] = self._format_addresses(to)
        message['Subject'] = Header(subject, 'utf-8')

        if cc:
            message['Cc'] = self._format_addresses(cc)
        if bcc:
            message['Bcc'] = self._format_addresses(bcc)

        return message

    @staticmethod
    def _format_addresses(addresses: Union[str, List[str]]) -> str:
        """格式化邮件地址"""
        if isinstance(addresses, str):
            return addresses
        return ', '.join(addresses)

    @staticmethod
    def _get_all_recipients(
        to: Union[str, List[str]],
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None
    ) -> List[str]:
        """获取所有收件人列表"""
        recipients = []

        if isinstance(to, str):
            recipients.append(to)
        else:
            recipients.extend(to)

        if cc:
            if isinstance(cc, str):
                recipients.append(cc)
            else:
                recipients.extend(cc)

        if bcc:
            if isinstance(bcc, str):
                recipients.append(bcc)
            else:
                recipients.extend(bcc)

        return recipients

    @staticmethod
    def _attach_file(message: MIMEMultipart, file_path: Union[str, Path]):
        """
        添加附件到邮件

        Args:
            message: 邮件对象
            file_path: 文件路径
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"附件文件不存在: {file_path}")

        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={file_path.name}'
        )
        message.attach(part)

    async def _send_via_smtp(self, message: MIMEMultipart, recipients: List[str]):
        """
        通过 SMTP 发送邮件

        Args:
            message: 邮件对象
            recipients: 收件人列表
        """
        try:
            # 在线程池中执行阻塞的 SMTP 操作
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_sync,
                message,
                recipients
            )
        except smtplib.SMTPAuthenticationError as e:
            raise EmailSendError(f"SMTP 认证失败，请检查邮箱和密码: {e}")
        except smtplib.SMTPException as e:
            raise EmailSendError(f"SMTP 发送失败: {e}")
        except Exception as e:
            raise EmailSendError(f"邮件发送失败: {e}")

    def _send_sync(self, message: MIMEMultipart, recipients: List[str]):
        """同步发送邮件（在线程池中执行）"""
        server = None
        try:
            # 建立连接
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                server.starttls()

            # 登录
            server.login(self.config.sender_email, self.config.sender_password)

            # 发送
            server.sendmail(self.config.sender_email, recipients, message.as_string())
        finally:
            if server:
                try:
                    server.quit()
                except (smtplib.SMTPException, OSError):
                    pass

    @async_retry(max_retries=3, delay=1.0)
    async def send_text_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        content: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None
    ) -> bool:
        """
        发送纯文本邮件

        Args:
            to: 收件人
            subject: 邮件主题
            content: 邮件内容（纯文本）
            cc: 抄送（可选）
            bcc: 密送（可选）

        Returns:
            是否发送成功
        """
        try:
            message = self._create_message(to, subject, cc, bcc)
            message.attach(MIMEText(content, 'plain', 'utf-8'))

            recipients = self._get_all_recipients(to, cc, bcc)
            await self._send_via_smtp(message, recipients)

            return True
        except Exception as e:
            raise EmailSendError(f"发送纯文本邮件失败: {e}")

    @async_retry(max_retries=3, delay=1.0)
    async def send_html_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        html_content: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None
    ) -> bool:
        """
        发送 HTML 邮件

        Args:
            to: 收件人
            subject: 邮件主题
            html_content: HTML 内容
            cc: 抄送（可选）
            bcc: 密送（可选）

        Returns:
            是否发送成功
        """
        try:
            message = self._create_message(to, subject, cc, bcc)
            message.attach(MIMEText(html_content, 'html', 'utf-8'))

            recipients = self._get_all_recipients(to, cc, bcc)
            await self._send_via_smtp(message, recipients)

            return True
        except Exception as e:
            raise EmailSendError(f"发送 HTML 邮件失败: {e}")

    @async_retry(max_retries=3, delay=1.0)
    async def send_email_with_attachments(
        self,
        to: Union[str, List[str]],
        subject: str,
        content: str,
        attachments: List[Union[str, Path]],
        is_html: bool = False,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None
    ) -> bool:
        """
        发送带附件的邮件

        Args:
            to: 收件人
            subject: 邮件主题
            content: 邮件内容
            attachments: 附件文件路径列表
            is_html: 内容是否为 HTML 格式
            cc: 抄送（可选）
            bcc: 密送（可选）

        Returns:
            是否发送成功
        """
        try:
            message = self._create_message(to, subject, cc, bcc)

            # 添加邮件内容
            content_type = 'html' if is_html else 'plain'
            message.attach(MIMEText(content, content_type, 'utf-8'))

            # 添加附件
            for attachment in attachments:
                self._attach_file(message, attachment)

            recipients = self._get_all_recipients(to, cc, bcc)
            await self._send_via_smtp(message, recipients)

            return True
        except Exception as e:
            raise EmailSendError(f"发送带附件邮件失败: {e}")
