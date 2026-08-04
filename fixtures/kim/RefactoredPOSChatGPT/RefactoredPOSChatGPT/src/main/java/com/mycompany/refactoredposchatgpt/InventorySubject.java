/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Observer Pattern: Subject
interface InventorySubject {
    void addObserver(InventoryObserver observer);
    void removeObserver(InventoryObserver observer);
    void notifyObservers(Item item, int newQuantity);
}
