/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

import java.text.DecimalFormat;

/**
 *
 * @author kim2
 */
// COMPOSITE PATTERN: Leaf class
class SaleLineItem implements SaleComponent {
    private Item item;
    private int quantity;

    public SaleLineItem(Item item, int quantity) {
        this.item = item;
        this.quantity = quantity;
    }
    
    @Override
    public double getTotal() {
        return item.getPrice() * quantity;
    }
    
    @Override
    public void print() {
        System.out.println("• " + item.getName() + "\t" + quantity + "\t\t$" + new DecimalFormat("##.00").format(getTotal()));
    }
    
    public String getItemName() {
        return item.getName();
    }
    
    public int getQuantity() {
        return quantity;
    }
}
