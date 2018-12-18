using System;
using System.Text;
// using MiscUtil.Conversion;

public static class Extensions
{
    public static string ToByteString(this byte[] byteArray)
    {
        var sb = new StringBuilder("(");
        for (var i = 0 ; i < byteArray.Length ; i++)
        {
            sb.Append(byteArray[i]);
            if (i < byteArray.Length - 1)
                sb.Append(", ");
        }
        sb.Append(")");
        return sb.ToString();
    }

    public static byte[] PaddedByteArray(this string input, int length)
    {
        if (input.Length > length)
            input = input.Substring(0, length);
        else
            input.PadRight(length, '\0');

        return Encoding.UTF8.GetBytes(input);
    }
}