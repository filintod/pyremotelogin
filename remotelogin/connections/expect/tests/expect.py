import unittest
from remotelogin.connections import expect

class MyTestCase(unittest.TestCase):

    def test_delete_element(self):
        e = expect.Expect('test').add_regex("hello", name="hello").add_regex("hello", name="hello2")
        self.assertIsNotNone(e['hello'])
        self.assertEquals(e['hello2'], e[1])
        e.delete("hello")
        with self.assertRaises(KeyError):
            e['hello']
        self.assertEquals(e['hello2'], e[0])


if __name__ == '__main__':
    unittest.main()
