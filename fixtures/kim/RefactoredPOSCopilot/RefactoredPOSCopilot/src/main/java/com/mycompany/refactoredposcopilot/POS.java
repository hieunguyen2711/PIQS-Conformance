/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

import java.util.List;

/**
 *
 * @author kim2
 */
class POS {
    private Sale s;
    private SaleLineItem sli;
    private List<SaleLineItem> slis;
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
        r.updateInventory(i, quantity);
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
