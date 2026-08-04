/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
// Observer Pattern: Concrete Observer
class InventoryLogger implements InventoryObserver {
    @Override
    public void update(Item item, int quantity) {
        System.out.println("Inventory updated: " + item.getName() + " x " + quantity);
    }
}