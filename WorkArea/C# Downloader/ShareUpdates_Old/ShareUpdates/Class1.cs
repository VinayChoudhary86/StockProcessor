using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ShareUpdates
{
    public class ListNode
    {
       public int val;
       public ListNode next;
       public ListNode(int val = 0, ListNode next = null)
       {
            this.val = val;
            this.next = next;
       }
    }
    class Class1
    {

        // Array sum for a Target
        public int[] TwoSum(int[] nums, int target)
        {
            Dictionary<int, int> dict = new Dictionary<int, int>();
            for (int i = 0; i < nums.Length; i++)
            {
                int a = target - nums[i];
                if (dict.ContainsKey(a))
                {
                    int index = 0;
                    dict.TryGetValue(a, out index);
                    return new int[] { index, i };
                }
                dict.Add(nums[i], i);
            }
            return nums;
        }

        // Add Two Numbers Linked List
        public ListNode AddTwoNumbers(ListNode l1, ListNode l2)
        {
            ListNode dummy = new ListNode(0);
            ListNode curr = dummy;
            int carry = 0;
            while (l1 != null || l2 != null)
            {
                int x = (l1 != null) ? l1.val : 0;
                int y = (l2 != null) ? l2.val : 0;
                int sum = x + y + carry;
                carry = sum / 10;
                curr.next = new ListNode(sum % 10);
                curr = curr.next;

                if (l1 != null) l1 = l1.next;
                if (l2 != null) l2 = l2.next;
            }
            if (carry > 0) curr.next = new ListNode(carry);

            return dummy.next;
        }

        // Max length string for non repeating characters
        public static string LengthOfLongestSubstring(string s)
        {
            int len = s.Length;
            char[] charArray = s.ToCharArray();
            string longestPalin = string.Empty;
            int longestPalinLen = 0;
            int palinLen = 0;
            for (int i = 0; i <= len; i++)
            {
                charArray[i] = s[len - i - 1];
            }

            for (int i = 0; i < len; i++)
            {
                int currPalinLen = 0;
                //int endIndex = ;
                int startIndex = i;
                for (int j = len - i - 1; j >= 0; j--)
                {
                    if (charArray[len - i - 1] == s[i])
                    {
                        currPalinLen++;
                    }
                    else
                    {
                        if (currPalinLen > longestPalinLen)
                        {
                            longestPalinLen = currPalinLen;
                            longestPalin = s.Substring(startIndex, longestPalinLen);
                            //startIndex = j;
                        }
                        break;
                    }
                }
            }

            return longestPalin;
        }
    }
}

