/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposgemini;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// Composite Pattern: Sale and SaleLineItem
class Sale {
    private List<SaleLineItem> items = new ArrayList<>();

    public void addItem(SaleLineItem item) {
        items.add(item);
    }

    public double getTotal() {
        double total = 0;
        for (SaleLineItem item : items) {
            total += item.getSubtotal();
        }
        return total;
    }
}
