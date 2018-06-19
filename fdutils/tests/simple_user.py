from fdutils.user import User, Group

__author__ = 'Filinto Duran (duranto@gmail.com)'
import unittest

class TestSimpleUser(unittest.TestCase):

    def test_group(self):

        CAN_DO_MAGIC = 1
        CAN_FLY = 1 << 2
        CAN_READ = 1 << 3

        U1 = User('filinto', 'duran',username='filinto')
        U2 = User('peter', 'pan', username='peter')
        U3 = User('harry', 'potter', username='harry')
        U4 = User('bat', 'man', username='bat')

        U1.add_capability(CAN_READ)
        U3.add_capability(CAN_DO_MAGIC)
        U2.add_capability(CAN_FLY)

        G1 = Group('root')
        G2 = Group('level1_1')
        G3 = Group('level1_2')
        G4 = Group('level2')
        G5, G6 = G4.add_by_name('level3_1', 'level3_2')
        G7 = G5.add_by_name('level4')

        G1.add_user(U1)
        G1.add(G2, G3)
        G2.add(G4)
        self.assertTrue(G1.find(G4.name) == G4)
        self.assertTrue(G1.get_user('filinto') == U1)
        G3.add_user(U3)
        G2.add_user(U2)
        self.assertTrue(set([u for u in G1.get_all_users()]) == {U1, U2, U3})
        self.assertTrue(set([u for u in G1.get_users_capable_of(CAN_FLY)]) == {U2})
        self.assertTrue(set([u for u in G1.get_users_capable_of(CAN_READ | CAN_DO_MAGIC)]) == {U3, U1})
        # G1 -> G2, G3
        # G2 -> G4 -> G5, G6
        # G5 -> G7
        G7.add_user(U4)
        self.assertTrue(set([u for u in G1.get_all_users()]) == {U1, U2, U3, U4})
        G7.add_user(U1)
        self.assertTrue(len(G1) == 5)
        G1.remove_user_from_all(U1.username)
        self.assertTrue(len(G1) == 3)
        self.assertTrue(set(G1.get_all_users()) == {U2, U3, U4})
        G1.add_user(U1)
        self.assertTrue(set(G2.get_all_users()) == {U2, U4})
        G1.remove(G2.name)
        self.assertTrue(set(G1.get_all_users()) == {U1, U3})
        G1.add(G2)
        G1.add(G2)
        self.assertTrue(set(G1.get_all_users()) == {U1, U2, U3, U4})
        G1.remove(G2.name)
        self.assertTrue(set(G1.get_all_users()) == {U1, U3})



