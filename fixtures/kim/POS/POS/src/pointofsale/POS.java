/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package pointofsale;

import java.util.ArrayList;

/**
 *
 * @author kim2
 */
public class POS {
    private Sale s;
    private SaleLineItem sli;
    private ArrayList<SaleLineItem> slis;
    private Register r;
    private double total;
    String message;

    public POS() {
        System.out.println("\nNew POS has been initiated\n");
        r = new Register();
    }

    public void processSale() {
        s = new Sale();
        r.addSale(s);
    }

    public void enterItem(Item i, int quantity) throws Exception {
        if (!r.checkInventory(i, quantity)) {
            throw new Exception("Insufficient inventory for " + i.getName());
        }
        sli = new SaleLineItem(i, quantity);
        s.add(sli);
    }

    public void addInventory(Item item, int quantity) {
        r.addInventory(item, quantity);
    }

    public double getTotal() {
        slis = s.getSaleLineItem();
        total = 0;
        for (SaleLineItem slItem : slis) {
            total = total + slItem.getSubTotal();
        }
        return total;
    }
    
    public String makePayment(double total, String paymentType) throws Exception {
        message = r.makePayment(total, paymentType);
        return message;
    }
}