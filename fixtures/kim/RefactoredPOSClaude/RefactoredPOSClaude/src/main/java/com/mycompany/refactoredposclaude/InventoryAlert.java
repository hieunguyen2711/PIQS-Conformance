/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
// OBSERVER PATTERN: Concrete observer for inventory alerts
class InventoryAlert implements InventoryObserver {
    private int threshold;
    
    public InventoryAlert(int threshold) {
        this.threshold = threshold;
    }
    
    @Override
    public void update(Item item, int newQuantity) {
        if (newQuantity < threshold) {
            System.out.println("ALERT: Low inventory for " + item.getName() + ". Current quantity: " + newQuantity);
        }
    }
}