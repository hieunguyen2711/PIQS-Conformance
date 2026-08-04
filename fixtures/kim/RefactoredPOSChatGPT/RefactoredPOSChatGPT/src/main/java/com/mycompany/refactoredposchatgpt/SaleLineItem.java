/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Composite Pattern: Leaf
class SaleLineItem extends SaleComponent {
    private Item item;
    private int quantity;

    public SaleLineItem(Item item, int quantity) {
        this.item = item;
        this.quantity = quantity;
    }

    @Override
    public double getSubTotal() {
        return item.getPrice() * quantity;
    }

    @Override
    public void display() {
        System.out.printf("\u2022 %s\t%d\t%.2f\n", item.getName(), quantity, getSubTotal());
    }
}
