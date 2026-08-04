/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
class POS {
    private Register register;
    private Sale currentSale;

    public POS() {
        System.out.println("\nNew POS has been initiated\n");
        register = new Register();
    }

    public void addInventory(Item item, int quantity) {
        register.addInventory(item, quantity);
    }

    public void startNewSale() {
        currentSale = new Sale();
        register.addSale(currentSale);
        System.out.println("\nStarting New Sale Process\n");
    }

    public void enterItem(Item item, int quantity) throws Exception {
        if (!register.checkInventory(item, quantity)) {
            throw new Exception("Insufficient inventory for " + item.getName());
        }
        SaleLineItem sli = new SaleLineItem(item, quantity);
        currentSale.addComponent(sli);
        register.updateInventory(item, quantity);
    }

    public void endSale() {
        currentSale.print();
    }

    public void makePayment(String paymentType) throws Exception {
        register.makePayment(currentSale.getTotal(), paymentType);
    }
}
