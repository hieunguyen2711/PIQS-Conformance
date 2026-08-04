/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Observer Pattern: Concrete Observer
class StockAlert implements InventoryObserver {
    private int threshold;

    public StockAlert(int threshold) {
        this.threshold = threshold;
    }

    @Override
    public void update(Item item, int newQuantity) {
        if (newQuantity < threshold) {
            System.out.printf("Alert: Low stock for %s. Remaining: %d\n", item.getName(), newQuantity);
        }
    }
}
