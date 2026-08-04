/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// Composite Pattern: Composite
class Sale extends SaleComponent {
    private List<SaleComponent> lineItems = new ArrayList<>();

    public void add(SaleComponent lineItem) {
        lineItems.add(lineItem);
    }

    @Override
    public double getSubTotal() {
        return lineItems.stream().mapToDouble(SaleComponent::getSubTotal).sum();
    }

    @Override
    public void display() {
        for (SaleComponent lineItem : lineItems) {
            lineItem.display();
        }
    }
}