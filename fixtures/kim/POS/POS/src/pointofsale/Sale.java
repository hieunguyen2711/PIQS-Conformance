/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package pointofsale;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Date;

/**
 *
 * @author kim2
 */
public class Sale {

    private DecimalFormat dfMoney = new DecimalFormat("$##.00");
    private ArrayList<SaleLineItem> slis = new ArrayList<>(); 
    private Date date;

    

    public Sale() {
    }
    
    public ArrayList<SaleLineItem> getSaleLineItem() {
        return slis;
    }
    
    public void add(SaleLineItem sli){
        slis.add(sli);
        System.out.println("• "+sli.getItemName()+ "\t1\t\t" + dfMoney.format(sli.getSubTotal()));
    }

    
}
