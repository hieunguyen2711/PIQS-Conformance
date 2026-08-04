/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposmeta;

import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// Composite Pattern: Composite
class Sale implements SaleComponent {
    private List<SaleComponent> components = new ArrayList<>();

    public void addComponent(SaleComponent component) {
        components.add(component);
    }

    @Override
    public double getSubTotal() {
        double total = 0;
        for (SaleComponent component : components) {
            total += component.getSubTotal();
        }
        return total;
    }
}