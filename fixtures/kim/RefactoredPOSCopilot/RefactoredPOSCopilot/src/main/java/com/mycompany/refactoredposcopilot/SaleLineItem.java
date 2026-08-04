/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

/**
 *
 * @author kim2
 */
class SaleLineItem {
    private Item item;
    private int quantity;

    public SaleLineItem(Item item, int quantity) {
        this.item = item;
        this.quantity = quantity;
    }

    public double getSubTotal() {
        return item.getPrice() * quantity;
    }

    public String getItemName() {
        return item.getName();
    }

    public int getQuantity() {
        return quantity;
    }
}
