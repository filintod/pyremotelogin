# import unittest
#
# from fdutils.decorators import exec_async, can_be_async
# from fdutils.lists import sort_nested_dict, to_sequence, del_from_list, del_elements_in_list_if_condition
# from fdutils.observable import ObservableEvents, EventSection
#
#
# class TestUtils(unittest.TestCase):
#
#     def test_sort_dict_of_dict(self):
#         a = dict(x=dict(b=1, c=8, d=3), y=dict(b=3, c=4, d=4), z=dict(b=2, c=6, d=1))
#         r = sort_nested_dict(a, 'c')
#         self.assertTrue([k[0] for k in r] == ['y', 'z', 'x'])
#
#     def test_sort_dict_of_dict_with_lambda(self):
#         a = dict(x=dict(b=1, c=-1, d=3), y=dict(b=3, c=4, d=4), z=dict(b=2, c=6, d=1))
#         r = sort_nested_dict(a, 'c', condition=lambda x: x * -1)
#         # z[c] would be -6 that will be the minimum value
#         self.assertTrue([k[0] for k in r] == ['z', 'y', 'x'])
#
#     def test_to_sequence(self):
#         self.assertTrue(to_sequence(1) == [1])
#         self.assertTrue(to_sequence([1]) == [1])
#         self.assertTrue(1 in to_sequence(1, seq_type=dict).keys())
#         self.assertTrue(to_sequence(None) == [])
#
#     def test_get_args_default(self):
#         def f(a, b, c, d=1, e=2, f=3):
#             pass
#
#         # test complete missing
#         kwargs = dict(e=5)
#         d = complete_function_defaults(f, **kwargs)
#         self.assertTrue(d['d'] == 1 and d['e'] == 5 and d['f'] == 3)
#
#         def f(a, b, c, d=1, e=2, f=3):
#             pass
#
#         # test new kwarg
#         kwargs = dict(g=5)
#         d = complete_function_defaults(f, **kwargs)
#         self.assertTrue(d['d'] == 1 and d['e'] == 2 and d['f'] == 3 and d['g'] == 5)
#
#         def f(a, b, c, d=1, e=2, f=3):
#             pass
#
#         # test args
#         args = (1, 2, 3)
#         d = complete_function_defaults_and_args(f, *args, **kwargs)
#         self.assertTrue(d.args[0] == 1 and d.args[1] == 2 and d.args[2] == 3)
#
#         def f(a, b, c, d=1, e=2, f=3):
#             pass
#
#         # test args
#         args = (1, 2, 3)
#         d = complete_function_defaults_and_args(f, *args, **kwargs)
#         self.assertTrue(d.args[0] == 1 and d.args[1] == 2 and d.args[2] == 3)
#
#         def f(a, b, c, d=1, e=2, f=3):
#             pass
#
#         # test args with some kwargs given only the value
#         args = (1, 2, 3, 5)     # d = 5
#         d = complete_function_defaults_and_args(f, *args, **kwargs)
#         e = complete_function_defaults_and_args(f, *d.args, **d.kwargs)
#         self.assertTrue(d.kwargs == e.kwargs)
#         self.assertTrue(d.args[0] == 1 and d.args[1] == 2 and d.args[2] == 3 and d.kwargs['d'] == 5)
#
#         # test what happen if no kwargs
#         def f(a, b, c):
#             pass
#         kwargs = {}
#         d = complete_function_defaults_and_args(f, *args, **kwargs)
#         self.assertTrue(d.args[0] == 1 and d.args[1] == 2 and d.args[2] == 3)
#
#         def f(a, b, c):
#             pass
#
#         # test SyntaxError keyword argument repeated
#         kwargs = dict(d=5)
#         args = (1, 2, 3, 5)     # d = 5
#         with self.assertRaises(SyntaxError):
#             complete_function_defaults_and_args(f, *args, **kwargs)
#
#         def g(a=1, b=2, c=3):
#             pass
#
#         args = (1,2,3)
#         d = complete_function_defaults_and_args(g, *args)
#
#     def test_del_from_list(self):
#
#         # delete single element
#         my_list = [1, 2, 3, 4, 5]
#         r = del_from_list(my_list, 2)
#         self.assertTrue(len(my_list) == 4)
#         self.assertTrue(2 not in my_list)
#         self.assertTrue(r > 0)
#
#         # delete all repeated
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_from_list(my_list, 2)
#         self.assertTrue(len(my_list) == 3)
#         self.assertTrue(2 not in my_list)
#         self.assertTrue(r == 3)
#
#         # delete only one
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_from_list(my_list, 2, count=1)
#         self.assertTrue(len(my_list) == 5)
#         self.assertTrue(2 in my_list)
#         self.assertTrue(r == 1)
#
#         # try to remove a non-existent element
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_from_list(my_list, 6)
#         self.assertTrue(len(my_list) == 6)
#         self.assertTrue(r == 0)
#
#         # try to delete more than one value
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_from_list(my_list, (1, 3))
#         self.assertTrue(len(my_list) == 4)
#         self.assertTrue(r == 2)
#
#         # try to delete more than one value but delete at most 3 elements
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_from_list(my_list, (1, 2), count=3)
#         self.assertTrue(len(my_list) == 3)
#         self.assertTrue(r == 3)
#         self.assertTrue(my_list == [3, 2, 5])
#
#     def test_del_from_list_if(self):
#
#         # delete single element
#         my_list = [1, 2, 3, 4, 5]
#         r = del_elements_in_list_if_condition(my_list, (lambda v: v == 2))
#         self.assertTrue(len(my_list) == 4)
#         self.assertTrue(2 not in my_list)
#         self.assertTrue(r > 0)
#
#         # delete all whose value is less than 3
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_elements_in_list_if_condition(my_list, (lambda v: v < 3))
#         self.assertTrue(len(my_list) == 2)
#         self.assertTrue(all([x not in my_list for x in (1, 2)]))
#         self.assertTrue(r == 4)
#
#         # delete one whose value is less than 3
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_elements_in_list_if_condition(my_list, (lambda v: v < 3), count=1)
#         self.assertTrue(len(my_list) == 5)
#         self.assertTrue(2 in my_list and 1 not in my_list)
#         self.assertTrue(r == 1)
#
#         # try to remove a non-existent element
#         my_list = [1, 2, 3, 2, 2, 5]
#         r = del_elements_in_list_if_condition(my_list, (lambda v: v < 0))
#         self.assertTrue(len(my_list) == 6)
#         self.assertTrue(r == 0)
#
#
#     def test_timer_running(self):
#         t0 = time.time()
#         for ok in timer_running(5, sleep=.5, raise_exception_if_timeout=False):
#             print 1
#
#         self.assertTrue((time.time() - t0) >= 5)
#
#         with self.assertRaises(TimeoutError):
#             for ok in timer_running(5, 6):
#                 print 'should raise exception'
#
#     def test_Timer(self):
#         import time
#
#         try:
#             t2 = SimpleTimer(5)
#             i = 1
#             with t2:
#                 while not t2.has_expired:
#
#                     time.sleep(1)
#                     print 't' + str(i)
#
#                     i += 1
#         except TimeoutError:
#             print 'Exception Found'
#         except Exception, e:
#             print e.message
#
#         try:
#             with SimpleTimer(0):
#                 time.sleep(1)
#             self.assertTrue(True)
#         except TimeoutError:
#             self.assertTrue(False)
#
#         with self.assertRaises(ValueError):
#             with SimpleTimer(-10):
#                 time.sleep(1)
#
#         # nested timers exceptions raise where
#         i = j = 1
#         with self.assertRaises(TimeoutError):
#             with SimpleTimer(10) as t:
#                 while True and not t.has_expired:
#                     time.sleep(.5)
#                     print 't1 ' + str(j)
#                     j += .5
#                     with SimpleTimer(10) as t2:
#                         while True and not t2.has_expired:
#                             time.sleep(.5)
#                             print 't2 ' + str(i)
#                             i += .5
#         self.assertTrue(t.has_expired)
#         self.assertTrue(t2.has_expired)
#
#     def test_callbacks(self):
#         results1 = [0]
#         results2 = [0]
#
#         def f1(a, b=0):
#             results1[0] = a + b
#
#         def f1_2(a):
#             results1[0] *= a
#
#         def f1_3(a):
#             results1[0] += a
#
#         def f2(a, b=0):
#             results2[0] = a - b
#
#         c = ObservableEvents()
#         c.add('f1', f1, (1, 2))
#         c.execute_all()
#         self.assertTrue(results1[0] == 3)
#
#         s = EventSection(c)
#         with s('before', 'after'):
#             print 'hello'
#
#         o12 = c.add('f1', f1_2, (2,))
#         c.execute_events()
#         self.assertTrue(results1[0] == 6)
#
#         c.remove_observer(o12, 'f1')
#         c.execute_events()
#         self.assertTrue(results1[0] == 3)
#
#         o1 = c.add('f1', f1_2, (2,))     # multiply by 2 => 6
#         o2 = c.add('f1', f1_3, (3,))     # add 3 => 9
#         o3 = c.add('f1', f1_2, (2,))     # multiply by 2 => 18
#         c.execute_events()
#         self.assertTrue(results1[0] == 18)
#
#         c.remove_observer_by_index(1, 'f1')   # remove o1
#         c.execute_events()
#         self.assertRaises(results1[0] == 12)
#
#         c.add('f1', f1_2, (2,), insert_at=1)    # insert back
#         c.execute_events()
#         self.assertRaises(results1[0] == 18)
#
#         c.remove('f1')
#         self.assertTrue(c.list_events() == [])
#
#         c.add('f1', f1, (), dict(a=5, b=6))
#         c.execute_events()
#         self.assertTrue(results1[0] == 11)
#
#         c.add('f2', f2, (5,), dict(b=3))
#         c.execute_events({'f1'})
#         self.assertTrue(results2[0] == 0)
#
#         c.execute_events()
#         self.assertTrue(results2[0] == 2)
#
#         with self.assertRaises(KeyError):
#             c.execute_events({'f3'})
#
#     def test_exec_async(self):
#         results = [0]
#         wait_for_me = [True]
#
#         @exec_async
#         def f1(a, b=0):
#             for i in range(10):
#                 print i
#                 results[0] = (i, a, b)
#                 while wait_for_me[0]:
#                     time.sleep(1)
#                 time.sleep(1)
#
#         t = f1(1, 2)
#         self.assertTrue(results[0] == (0, 1, 2))
#         wait_for_me[0] = False
#         t.join()
#
#     def test_exec_async_can_be_async(self):
#
#         results = [0]
#         wait_for_me = [True]
#
#         def f1(a, b=0):
#             for i in range(10):
#                 print i
#                 results[0] = (i, a, b)
#                 while wait_for_me[0]:
#                     time.sleep(1)
#                 time.sleep(1)
#
#         t = exec_async(f1)(1, 2)
#         self.assertTrue(results[0] == (0, 1, 2))
#         wait_for_me[0] = False
#         t.join()
#
#     def test_exec_async_can_be_async_2(self):
#
#         results = [0]
#         wait_for_me = [True]
#
#         def f1(a, b=0):
#             for i in range(10):
#                 print i
#                 results[0] = (i, a, b)
#                 while wait_for_me[0]:
#                     time.sleep(1)
#                 time.sleep(1)
#
#         t = exec_async(f1)(1, 2)
#         self.assertTrue(results[0] == (0, 1, 2))
#         wait_for_me[0] = False
#         t.join()
#
#     def test_can_be_async_exec_async(self):
#
#         results = [0]
#         wait_for_me = [True]
#
#         def f1(a, b=0):
#             for i in range(10):
#                 print i
#                 results[0] = (i, a, b)
#                 while wait_for_me[0]:
#                     time.sleep(1)
#                 time.sleep(1)
#
#         t = can_be_async(f1)(1, 2)
#         self.assertTrue(results[0] == (0, 1, 2))
#         wait_for_me[0] = False
#         t.join()
#
#     def test_secs_hours_mins(self):
#         self.assertTrue(seconds_to_hour_min_sec(60) == '00:01:00')
#         self.assertTrue(seconds_to_hour_min_sec(3600) == '01:00:00')
#         self.assertTrue(seconds_to_hour_min_sec(7200) == '02:00:00')
#         self.assertTrue(seconds_to_hour_min_sec(7230) == '02:00:30')
#         self.assertTrue(seconds_to_hour_min_sec(1230) == '00:20:30')
#         self.assertTrue(seconds_to_hour_min_sec(1230.5) == '00:20:30')
#
#     def test_upload_broker(self):
#
#         with open('test_file.csv', 'w') as f:
#             f.write('hello world')
#
#         self.assertTrue(upload_file_to_remote_broker('test_file.csv'))
#
#
