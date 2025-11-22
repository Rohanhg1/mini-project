import sys
sys.path.insert(0, r'c:\Users\Rohan H G\OneDrive\Desktop\cse_1')
from project.app.views import allocate_timetable_with_rest
import pprint

entries = [
    {'teacher':'T1','year':1,'subject':'Math','hours':3,'is_lab':False,'remaining':3},
    {'teacher':'T2','year':1,'subject':'Physics','hours':4,'is_lab':False,'remaining':4},
    {'teacher':'T1','year':2,'subject':'MathLab','hours':2,'is_lab':True,'remaining':2},
]

if __name__ == '__main__':
    tt, un = allocate_timetable_with_rest(entries)
    print('Year1 Mon:')
    pprint.pprint(tt[1]['Mon'])
    print('\nYear1 Tue:')
    pprint.pprint(tt[1]['Tue'])
    print('\nYear2 Mon:')
    pprint.pprint(tt[2]['Mon'])
    print('\nUnallocated:')
    pprint.pprint(un)
