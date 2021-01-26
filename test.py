# numbers = [(3, 14), (1, 61), (2, 71)]
# # 给元祖排序使用lambda
# numbers.sort(key=lambda k: k[0])
#
# print('Sorted list:', numbers)
import re

directions = ["Arya", "Daenerys", "Jon", "Brienne"]

directions.sort(key=lambda x : str(re.match(r'[n]',x)))

print('Sorted list:', directions)
