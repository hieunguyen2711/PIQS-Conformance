/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredposchatgpt;

/**
 *
 * @author kim2
 */
// Observer Pattern: Observer Interface
interface InventoryObserver {
    void update(Item item, int newQuantity);
}