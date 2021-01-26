from fdfs_client.client import Fdfs_client

if __name__ == '__main__':
    client = Fdfs_client('client.conf')
    # up = client.upload_by_filename('/home/a123/Desktop/aaa1.png')
    # print(up)
'''
{'Status': 'Upload successed.', 
'Group name': 'group1', 
'Storage IP': '192.168.0.108', 
'Uploaded size': '180.00KB', 
'Local file name': '/home/a123/Desktop/aaa1.png', 
'Remote file_id': 'group1/M00/00/02/wKgAbF6MMh2AFE5nAALTFWlkU6g801.png'}
'''