package cn.xbhel.flink.table;


import java.io.IOException;

public class Application {

    public static void main(String[] args) throws IOException {

        var phone = Double.valueOf("1.3812345678E10");
        java.text.DecimalFormat df = new java.text.DecimalFormat("0");
        String phoneStr = df.format(phone);
        System.out.println(phoneStr);

    }


}
