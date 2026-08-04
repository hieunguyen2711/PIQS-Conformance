/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package pointofsale;

/**
 *
 * @author kim2
 */
import java.util.HashMap;
import java.util.Map;

public class ItemInventory {
    private Map<Integer, Integer> inventory = new HashMap<>();
    
    public void addInventory(Item item, int quantity) {
        inventory.put(item.getID(), quantity);
    }
    
    public boolean checkAvailability(Item item, int quantity) {
        return inventory.getOrDefault(item.getID(), 0) >= quantity;
    }
    
    public void updateInventory(Item item, int quantity) {
        int currentQty = inventory.getOrDefault(item.getID(), 0);
        inventory.put(item.getID(), currentQty - quantity);
    }
}
