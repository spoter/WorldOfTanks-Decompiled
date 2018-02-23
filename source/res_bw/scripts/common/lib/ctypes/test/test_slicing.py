# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/common/Lib/ctypes/test/test_slicing.py
import unittest
from ctypes import *
import _ctypes_test

class SlicesTestCase(unittest.TestCase):

    def test_getslice_cint(self):
        a = (c_int * 100)(*xrange(1100, 1200))
        b = range(1100, 1200)
        self.assertEqual(a[0:2], b[0:2])
        self.assertEqual(a[0:2:], b[0:2:])
        self.assertEqual(len(a), len(b))
        self.assertEqual(a[5:7], b[5:7])
        self.assertEqual(a[5:7:], b[5:7:])
        self.assertEqual(a[-1], b[-1])
        self.assertEqual(a[:], b[:])
        self.assertEqual(a[::], b[::])
        self.assertEqual(a[10::-1], b[10::-1])
        self.assertEqual(a[30:20:-1], b[30:20:-1])
        self.assertEqual(a[:12:6], b[:12:6])
        self.assertEqual(a[2:6:4], b[2:6:4])
        a[0:5] = range(5, 10)
        self.assertEqual(a[0:5], range(5, 10))
        self.assertEqual(a[0:5:], range(5, 10))
        self.assertEqual(a[4::-1], range(9, 4, -1))
        return

    def test_setslice_cint(self):
        a = (c_int * 100)(*xrange(1100, 1200))
        b = range(1100, 1200)
        a[32:47] = range(32, 47)
        self.assertEqual(a[32:47], range(32, 47))
        a[32:47] = range(132, 147)
        self.assertEqual(a[32:47:], range(132, 147))
        a[46:31:-1] = range(232, 247)
        self.assertEqual(a[32:47:1], range(246, 231, -1))
        a[32:47] = range(1132, 1147)
        self.assertEqual(a[:], b)
        a[32:47:7] = range(3)
        b[32:47:7] = range(3)
        self.assertEqual(a[:], b)
        a[33::-3] = range(12)
        b[33::-3] = range(12)
        self.assertEqual(a[:], b)
        from operator import setslice, setitem
        self.assertRaises(TypeError, setslice, a, 0, 5, 'abcde')
        self.assertRaises(TypeError, setitem, a, slice(0, 5), 'abcde')
        self.assertRaises(TypeError, setslice, a, 0, 5, ['a',
         'b',
         'c',
         'd',
         'e'])
        self.assertRaises(TypeError, setitem, a, slice(0, 5), ['a',
         'b',
         'c',
         'd',
         'e'])
        self.assertRaises(TypeError, setslice, a, 0, 5, [1,
         2,
         3,
         4,
         3.14])
        self.assertRaises(TypeError, setitem, a, slice(0, 5), [1,
         2,
         3,
         4,
         3.14])
        self.assertRaises(ValueError, setslice, a, 0, 5, range(32))
        self.assertRaises(ValueError, setitem, a, slice(0, 5), range(32))
        return

    def test_char_ptr(self):
        s = 'abcdefghijklmnopqrstuvwxyz'
        dll = CDLL(_ctypes_test.__file__)
        dll.my_strdup.restype = POINTER(c_char)
        dll.my_free.restype = None
        res = dll.my_strdup(s)
        self.assertEqual(res[:len(s)], s)
        self.assertEqual(res[:3], s[:3])
        self.assertEqual(res[:len(s):], s)
        self.assertEqual(res[len(s) - 1:-1:-1], s[::-1])
        self.assertEqual(res[len(s) - 1:5:-7], s[:5:-7])
        self.assertEqual(res[0:-1:-1], s[0::-1])
        import operator
        self.assertRaises(ValueError, operator.getitem, res, slice(None, None, None))
        self.assertRaises(ValueError, operator.getitem, res, slice(0, None, None))
        self.assertRaises(ValueError, operator.getitem, res, slice(None, 5, -1))
        self.assertRaises(ValueError, operator.getitem, res, slice(-5, None, None))
        self.assertRaises(TypeError, operator.setslice, res, 0, 5, u'abcde')
        self.assertRaises(TypeError, operator.setitem, res, slice(0, 5), u'abcde')
        dll.my_free(res)
        dll.my_strdup.restype = POINTER(c_byte)
        res = dll.my_strdup(s)
        self.assertEqual(res[:len(s)], range(ord('a'), ord('z') + 1))
        self.assertEqual(res[:len(s):], range(ord('a'), ord('z') + 1))
        dll.my_free(res)
        return

    def test_char_ptr_with_free(self):
        dll = CDLL(_ctypes_test.__file__)
        s = 'abcdefghijklmnopqrstuvwxyz'

        class allocated_c_char_p(c_char_p):
            pass

        dll.my_free.restype = None

        def errcheck(result, func, args):
            retval = result.value
            dll.my_free(result)
            return retval

        dll.my_strdup.restype = allocated_c_char_p
        dll.my_strdup.errcheck = errcheck
        try:
            res = dll.my_strdup(s)
            self.assertEqual(res, s)
        finally:
            del dll.my_strdup.errcheck

        return

    def test_char_array(self):
        s = 'abcdefghijklmnopqrstuvwxyz\x00'
        p = (c_char * 27)(*s)
        self.assertEqual(p[:], s)
        self.assertEqual(p[::], s)
        self.assertEqual(p[::-1], s[::-1])
        self.assertEqual(p[5::-2], s[5::-2])
        self.assertEqual(p[2:5:-3], s[2:5:-3])
        return

    try:
        c_wchar
    except NameError:
        pass
    else:

        def test_wchar_ptr(self):
            s = u'abcdefghijklmnopqrstuvwxyz\x00'
            dll = CDLL(_ctypes_test.__file__)
            dll.my_wcsdup.restype = POINTER(c_wchar)
            dll.my_wcsdup.argtypes = (POINTER(c_wchar),)
            dll.my_free.restype = None
            res = dll.my_wcsdup(s)
            self.assertEqual(res[:len(s)], s)
            self.assertEqual(res[:len(s):], s)
            self.assertEqual(res[len(s) - 1:-1:-1], s[::-1])
            self.assertEqual(res[len(s) - 1:5:-7], s[:5:-7])
            import operator
            self.assertRaises(TypeError, operator.setslice, res, 0, 5, u'abcde')
            self.assertRaises(TypeError, operator.setitem, res, slice(0, 5), u'abcde')
            dll.my_free(res)
            if sizeof(c_wchar) == sizeof(c_short):
                dll.my_wcsdup.restype = POINTER(c_short)
            elif sizeof(c_wchar) == sizeof(c_int):
                dll.my_wcsdup.restype = POINTER(c_int)
            elif sizeof(c_wchar) == sizeof(c_long):
                dll.my_wcsdup.restype = POINTER(c_long)
            else:
                return
            res = dll.my_wcsdup(s)
            tmpl = range(ord('a'), ord('z') + 1)
            self.assertEqual(res[:len(s) - 1], tmpl)
            self.assertEqual(res[:len(s) - 1:], tmpl)
            self.assertEqual(res[len(s) - 2:-1:-1], tmpl[::-1])
            self.assertEqual(res[len(s) - 2:5:-7], tmpl[:5:-7])
            dll.my_free(res)
            return


if __name__ == '__main__':
    unittest.main()
