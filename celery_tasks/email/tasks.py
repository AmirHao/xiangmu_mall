from django.core.mail import send_mail
from django.conf import settings
from celery_tasks.main import celery_app

# 发送邮件任务
@celery_app.task(bind=True,name='send_verify_email',retry_backoff=3)
def send_verify_email(self,to_email,verify_url):
    """
        发送验证邮箱邮件
        :param to_email: 收件人邮箱
        :param verify_url: 验证链接
        :return: None
        """
    subject = "清美商城邮箱验证"
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用清美商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s<a></p>' % (to_email, verify_url, verify_url)
    try:
        send_mail(subject,'',settings.EMAIL_FROM,[to_email],html_message=html_message)
    except Exception as e:
        raise self.retry(exc=e,max_retries=3)
