/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// COMPOSITE PATTERN: Composite class
class Sale implements SaleComponent {
    private List<SaleComponent> components = new ArrayList<>();

    public void addComponent(SaleComponent component) {
        components.add(component);
    }
    
    @Override
    public double getTotal() {
        return components.stream().mapToDouble(SaleComponent::getTotal).sum();
    }
    
    @Override
    public void print() {
        System.out.println("\n=== SALE ===");
        System.out.println("  Item\t\tQuantity\tPrice");
        System.out.println("_______________________________________");
        components.forEach(SaleComponent::print);
        System.out.println("_______________________________________");
        System.out.println("Total: $" + new DecimalFormat("##.00").format(getTotal()));
    }
    
    public List<SaleComponent> getComponents() {
        return components;
    }
}
