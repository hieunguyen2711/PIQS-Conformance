/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredposmeta;

/**
 *
 * @author kim2
 */
// Observer Pattern: Subject interface
interface InventorySubject {
    void registerObserver(InventoryObserver observer);
    void removeObserver(InventoryObserver observer);
    void notifyObservers(Item item, int quantity);
}