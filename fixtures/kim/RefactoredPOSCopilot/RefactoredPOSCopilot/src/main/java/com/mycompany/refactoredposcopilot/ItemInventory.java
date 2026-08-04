/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 *
 * @author kim2
 */
class ItemInventory {
    private Map<Integer, Integer> inventory = new HashMap<>();
    private List<InventoryObserver> observers = new ArrayList<>();

    public void addObserver(InventoryObserver observer) {
        observers.add(observer);
    }

    public void removeObserver(InventoryObserver observer) {
        observers.remove(observer);
    }

    public void addInventory(Item item, int quantity) {
        inventory.put(item.getID(), quantity);
        notifyObservers(item, quantity);
    }

    public boolean checkAvailability(Item item, int quantity) {
        return inventory.getOrDefault(item.getID(), 0) >= quantity;
    }

    public void updateInventory(Item item, int quantity) {
        int currentQty = inventory.getOrDefault(item.getID(), 0);
        inventory.put(item.getID(), currentQty - quantity);
        notifyObservers(item, -quantity);
    }

    private void notifyObservers(Item item, int quantity) {
        for (InventoryObserver observer : observers) {
            observer.update(item, quantity);
        }
    }
}
