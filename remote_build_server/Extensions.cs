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
}